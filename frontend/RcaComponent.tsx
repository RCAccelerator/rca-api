import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./RcaComponent.css";

interface RcaComponentProps {
  build: string;
  backendUrl?: string;
}

interface Tokens {
  input: number;
  output: number;
}

function Spinner() {
  return (
    <div className="flex justify-center items-center p-8">
      <div className="w-16 h-16 border-4 border-blue-500 border-dashed rounded-full animate-spin"></div>
    </div>
  );
}

export function RcaComponent(
  { build = "", job = "", backendUrl = "" }: RcaComponentProps,
) {
  const [refresh, setRefresh] = useState(false);
  const [status, setStatus] = useState<string[]>([]);
  const [playbooks, setPlaybooks] = useState<string[]>([]);
  const [jobInfo, setJobInfo] = useState(null);
  const [result, setResult] = useState("");
  const [errors, setErrors] = useState([]);
  const [logjuicerUrl, setLogjuicerUrl] = useState("");
  const [usage, setUsage] = useState<Tokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const eventSourceRef = useRef<EventSource | null>(null);

  const addError = (e) => setErrors((prev) => [...prev, e])

  async function getReport() {
    setStatus([]);
    setJobInfo(null);
    setPlaybooks([]);
    setResult("");
    setErrors([]);
    setLogjuicerUrl("");
    setUsage(null);
    setIsLoading(true);

    if (!build && !job) {
      setStatus(
        (_) => ["Build is missing, try adding ?build=... to the page url."]
      );
      setIsLoading(false);
      return;
    }
    let eventSource;
    if (eventSource) {
      eventSource.close();
    }

    function handleMessage(event, body) {
      setIsLoading(false);
      switch (event) {
        case "progress":
          setStatus((prevStatus) => [...prevStatus, body]);
          break;
        case "chunk":
          setResult((prevResult) => prevResult + body);
          break;
        case "logjuicer_url":
          setLogjuicerUrl(body);
          break;
        case "playbooks":
          setPlaybooks(body);
          break;
        case "job":
          setJobInfo(body);
          break;
        case "usage":
          setUsage(body);
          break;
        case "redirect":
          if (eventSource) {
            eventSource.close();
          }
          eventSource = null;
          setRefresh(true);
          break;
        case "error":
          addError(body);
          break;
        case "status":
          console.log("Setting status", body);
          if (body != "completed") {
            addError(body);
          }
          if (eventSource) {
            eventSource.close();
          }
          eventSource = null;
          break;
      }
    }

    try {
      const arg = build ? `?build=${encodeURIComponent(build)}` : `_job?name=${job}`;
      const submitRes = await fetch(`${backendUrl}/get${arg}`, {method: "PUT"});

      const submitData = await submitRes.json();

      if (submitData instanceof Array) {
        submitData.forEach(([event, body]) => {
          handleMessage(event, body);
        });
        setIsLoading(false);
        return;
      }

      const watch_arg = build ? `?build=${encodeURIComponent(build)}` : `_job?name=${job}`;
      eventSource = new EventSource(`${backendUrl}/watch${watch_arg}`);

      eventSource.onmessage = (e) => {
        const [event, body] = JSON.parse(e.data);
        handleMessage(event, body);
      };

      eventSource.onerror = () => {
        addError(
          "Failed to connect to the server. Please ensure the backend is running and accessible.",
        );
        setIsLoading(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      };
    } catch (err) {
      console.error("RCA failed", err);
      addError(
        err instanceof Error ? err.message : "An unknown error occurred.",
      );
      setIsLoading(false);
    }
  }
  useEffect(() => {
    getReport();
    return () => { };
  }, [build, job, refresh]);
  return (
    <div className="flex flex-col items-center">
      <div className="w-full max-w-4xl">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold"><a href="https://github.com/RCAccelerator/rca-api"
              className="text-blue-600 dark:text-blue-400 hover:underline">RCAv2</a></h1>
          <p className="text-gray-600 dark:text-gray-400">
            Fast and accurate root cause analysis of Zuul CI Build failures.
          </p>
        </header>
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-8" role="alert">
          <p className="font-bold">RCAv2 experiment</p>
          <p>This box is powered by GenAI, the model can make mistakes, so double-check it</p>
        </div>
        <main className="w-full flex flex-col items-center gap-6">
          {isLoading && <Spinner />}
          {errors.length > 0 && (
            <div className="w-full bg-red-50 dark:bg-gray-800 border border-red-500 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-red-700 dark:text-red-400 border-b border-red-200 dark:border-gray-700 pb-2 mb-4">
                Error
              </h2>
              {errors.map((error, index) => (
                <pre key={index} className="text-red-600 dark:text-red-300 whitespace-pre-wrap break-words font-mono">{error}</pre>
              ))}
            </div>
          )}
          {!isLoading && (logjuicerUrl || status.length > 0) && (
            <div className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold border-b border-gray-200 dark:border-gray-700 pb-2 mb-4">
                Analysis Status
              </h2>
              {logjuicerUrl && (
                <div className="mb-4">
                  <a
                    href={logjuicerUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg transition-colors duration-200"
                  >
                    View logjuicer report
                  </a>
                </div>
              )}
              <ul className="list-none p-0 m-0 font-mono text-sm space-y-2">
                {status.map((msg, index) => (
                  <li key={index} className="pt-1 break-words">{msg}</li>
                ))}
              </ul>
            </div>
          )}
          {(jobInfo || playbooks.length > 0) && (
            <div className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg shadow-md p-6">
              <div className="flex flex-wrap justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 gap-2">
                <h2 className="text-xl font-semibold">
                  Job Information
                </h2>
              </div>
              <div className="mb-4 p-3 rounded-md border border-gray-200 dark:border-gray-600">
                {jobInfo && jobInfo.description && (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    pre: ({ node, ...props }) => (
                      <pre
                        {...props}
                        className="whitespace-pre-wrap break-all"
                      />
                    ),
                  }}
                >
                  {jobInfo.description}
                </ReactMarkdown>
                )}
              </div>
              {playbooks.length > 0 && (<>
                <h3 className="font-semibold">Playbooks</h3>
                <ul className="list-disc p-0 m-0 font-mono text-sm space-y-2 mb-3">
                  {playbooks.map((play, index) => (
                    <li key={index} className="pt-1 break-words">{play}</li>
                  ))}
                </ul>
              </>)}
              {jobInfo && jobInfo.actions && (<>
                <h3 className="font-semibold">Actions</h3>
                <ul className="list-decimal p-0 ml-3 font-mono text-sm space-y-2">
                  {jobInfo.actions.map((action, index) => (
                    <li key={index} className="pt-1 break-words">{action}</li>
                  ))}
                </ul>
              </>)}
            </div>
          )}
          {result && (
            <div className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg shadow-md p-6">
              <div className="flex flex-wrap justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-2 mb-4 gap-2">
                <h2 className="text-xl font-semibold">
                  Analysis Result
                </h2>
                {usage && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                    Tokens: {usage.input} in / {usage.output} out
                  </div>
                )}
              </div>
              <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-md border border-gray-200 dark:border-gray-600">
                <span className="font-semibold">Build URL: </span>
                <a
                  href={build}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline break-all"
                >
                  {build}
                </a>
              </div>
              <div className="prose dark:prose-invert max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    pre: ({ node, ...props }) => (
                      <pre
                        {...props}
                        className="whitespace-pre-wrap break-all"
                      />
                    ),
                  }}
                >
                  {result}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
