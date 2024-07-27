import { Readable } from 'stream';
import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';
import https from 'https';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  if (req.method === 'POST') {
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }
    
    const data = JSON.parse(Buffer.concat(chunks).toString());
    const { username, password, targetUsername } = data;
    
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    });
    
    const readable = new Readable({
      read() {},
    });
    
    readable.pipe(res);
    
    try {
      const browser = await puppeteer.launch();
      const page = await browser.newPage();
      
      // Login to Instagram
      await page.goto('https://www.instagram.com/accounts/login/');
      await page.type('input[name="username"]', username);
      await page.type('input[name="password"]', password);
      await page.click('button[type="submit"]');
      await page.waitForNavigation();
      
      readable.push(JSON.stringify({ type: 'progress', value: 25 }));
      
      // Navigate to DMs
      await page.goto('https://www.instagram.com/direct/inbox/');
      await page.waitForSelector('input[placeholder="Search"]');
      
      readable.push(JSON.stringify({ type: 'progress', value: 50 }));
      
      // Search for target user
      await page.type('input[placeholder="Search"]', targetUsername);
      await page.waitForSelector(`span[title="${targetUsername}"]`);
      await page.click(`span[title="${targetUsername}"]`);
      
      readable.push(JSON.stringify({ type: 'progress', value: 75 }));
      
      // Find and download reels
      const reels = await page.evaluate(() => {
        const reelElements = Array.from(document.querySelectorAll('div[role="button"]'));
        return reelElements
          .filter(el => el.textContent.includes('Reel'))
          .map(el => {
            const link = el.querySelector('a');
            return link ? link.href : null;
          })
          .filter(Boolean);
      });
      
      const downloadPath = path.join(process.cwd(), 'downloads');
      if (!fs.existsSync(downloadPath)) {
        fs.mkdirSync(downloadPath);
      }
      
      for (let i = 0; i < reels.length; i++) {
        const reelUrl = reels[i];
        await page.goto(reelUrl);
        
        const videoUrl = await page.evaluate(() => {
          const videoElement = document.querySelector('video');
          return videoElement ? videoElement.src : null;
        });
        
        if (videoUrl) {
          const fileName = `reel_${i + 1}.mp4`;
          const filePath = path.join(downloadPath, fileName);
          
          await new Promise((resolve, reject) => {
            https.get(videoUrl, (response) => {
              const fileStream = fs.createWriteStream(filePath);
              response.pipe(fileStream);
              fileStream.on('finish', () => {
                fileStream.close();
                resolve();
              });
            }).on('error', reject);
          });
          
          readable.push(JSON.stringify({ type: 'progress', value: 75 + (25 * (i + 1) / reels.length) }));
        }
      }
      
      readable.push(JSON.stringify({ type: 'progress', value: 100 }));
      readable.push(JSON.stringify({ type: 'result', value: `Successfully downloaded ${reels.length} reels` }));
      
      await browser.close();
    } catch (error) {
      readable.push(JSON.stringify({ type: 'result', value: `Error: ${error.message}` }));
    }
    
    readable.push(null);
  } else {
    res.status(405).json({ message: 'Method Not Allowed' });
  }
}