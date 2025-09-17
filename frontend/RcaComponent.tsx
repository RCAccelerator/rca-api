import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './RcaComponent.css';

interface RcaComponentProps {
  backendUrl?: string;
}

function RcaComponent({ backendUrl = '' }: RcaComponentProps) {
  const [buildUrl, setBuildUrl] = useState('');
  const [status, setStatus] = useState<string[]>([]);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!buildUrl || isLoading) return;

    setIsLoading(true);
    setStatus([]);
    setResult('');
    setError('');

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const submitRes = await fetch(`${backendUrl}/submit?build=${encodeURIComponent(buildUrl)}`, {
        method: 'PUT',
      });

      const submitData = await submitRes.json();

      if (submitData.status === 'COMPLETED') {
        const reportRes = await fetch(`${backendUrl}/report?build=${encodeURIComponent(buildUrl)}`);
        if (!reportRes.ok) {
          throw new Error('Failed to fetch completed report');
        }
        const reportJson = await reportRes.json();
        const fullReport = reportJson
          .filter(([event]: [string, string]) => event === 'chunk')
          .map(([, body]: [string, string]) => body)
          .join('');
        setResult(fullReport);
        setIsLoading(false);
        return;
      }

      const eventSource = new EventSource(`${backendUrl}/watch?build=${encodeURIComponent(buildUrl)}`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (e) => {
        const [event, body] = JSON.parse(e.data);
        switch (event) {
          case 'progress':
            setStatus((prevStatus) => [...prevStatus, body]);
            break;
          case 'chunk':
            setResult((prevResult) => prevResult + body);
            break;
          case 'status':
            setIsLoading(false);
            eventSource.close();
            eventSourceRef.current = null;
            break;
        }
      };

      eventSource.onerror = () => {
        setError('Failed to connect to the server. Please ensure the backend is running and accessible.');
        setIsLoading(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-white min-h-screen flex flex-col items-center p-4 sm:p-6 lg:p-8 transition-colors duration-300">
      <div className="w-full max-w-4xl">
        <header className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-bold text-center">RCAv2</h1>
        </header>
        <main className="w-full flex flex-col items-center gap-6">
          <form onSubmit={handleSubmit} className="w-full flex flex-col sm:flex-row gap-4">
            <input
              type="url"
              value={buildUrl}
              onChange={(e) => setBuildUrl(e.target.value)}
              placeholder="Enter build URL"
              required
              disabled={isLoading}
              className="flex-grow bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none disabled:opacity-50 transition-colors duration-300"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-transform duration-200 active:scale-95"
            >
              {isLoading ? 'Analyzing...' : 'Analyze'}
            </button>
          </form>

          {error && (
            <div className="w-full bg-red-50 dark:bg-gray-800 border border-red-500 rounded-md p-4">
              <h2 className="text-xl font-semibold text-red-700 dark:text-red-400 border-b border-red-200 dark:border-gray-700 pb-2 mb-3">Error</h2>
              <pre className="text-red-600 dark:text-red-300 whitespace-pre-wrap break-words font-mono">{error}</pre>
            </div>
          )}

          {status.length > 0 && (
            <div className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md p-4">
              <h2 className="text-xl font-semibold border-b border-gray-200 dark:border-gray-700 pb-2 mb-3">Analysis Status</h2>
              <ul className="list-none p-0 m-0 font-mono text-sm">
                {status.map((msg, index) => (
                  <li key={index} className="pt-1">{msg}</li>
                ))}
              </ul>
            </div>
          )}

          {result && (
            <div className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md p-4">
              <h2 className="text-xl font-semibold border-b border-gray-200 dark:border-gray-700 pb-2 mb-3">Analysis Result</h2>
              <div className="prose dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default RcaComponent;