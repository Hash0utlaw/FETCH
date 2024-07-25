'use client'
import React, { useState, FormEvent } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardHeader, CardContent } from "@/components/ui/card";

interface Update {
  type: 'progress' | 'result';
  value: number | string;
}

const FetchApp: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [targetUsername, setTargetUsername] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState('');

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setProgress(0);
    setResult('');

    try {
      const response = await fetch('/api/fetch-reels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, targetUsername }),
      });

      if (response.ok) {
        const reader = response.body!.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          
          const decodedChunk = decoder.decode(value, { stream: true });
          const updates: Update[] = decodedChunk
            .split('\n')
            .filter(Boolean)
            .map((line) => JSON.parse(line) as Update);
          
          updates.forEach(update => {
            if (update.type === 'progress') {
              setProgress(update.value as number);
            } else if (update.type === 'result') {
              setResult(update.value as string);
            }
          });
        }
      } else {
        setResult('Error occurred while fetching reels');
      }
    } catch (error) {
      setResult(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="max-w-md mx-auto mt-10">
      <CardHeader>
        <h1 className="text-2xl font-bold text-center">FETCH Instagram Reels</h1>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            type="text"
            placeholder="Instagram Username"
            value={username}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Instagram Password"
            value={password}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
            required
          />
          <Input
            type="text"
            placeholder="Target Username"
            value={targetUsername}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTargetUsername(e.target.value)}
            required
          />
          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? 'Fetching...' : 'Fetch Reels'}
          </Button>
        </form>
        {isLoading && <Progress value={progress} className="mt-4" />}
        {result && (
          <div className="mt-4 p-4 bg-gray-100 rounded">
            <h2 className="font-semibold">Result:</h2>
            <p>{result}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default FetchApp;