import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./RcaComponent.css";

function Spinner() {
  return (
    <div className="flex justify-center items-center p-8">
      <div className="w-16 h-16 border-4 border-blue-500 border-dashed rounded-full animate-spin">
      </div>
    </div>
  );
}

function Evidence({ error, source, log_url, logjuicer_url, source_map }) {
  return (
    <div>
      <div className="bg-slate-100">
        <a
          href={log_url + "/" + source}
          target="_blank"
          rel="noopener noreferrer"
          className="cursor-pointer hover:underline"
        >
          {source}
        </a>
        <a
          href={logjuicer_url + "#lr-" + source_map[source]}
          target="_blank"
          rel="noopener noreferrer"
          className="cursor-pointer bg-blue-500 hover:underline rounded-lg text-white mx-2"
        >
          logjuicer
        </a>
      </div>
      <pre className="pl-2 font-mono break-all whitespace-pre-wrap">{error}</pre>
    </div>
  );
}

export function RcaComponent(
  { build = "", workflow = "", backendUrl = "", setID = null },
) {
  const [status, setStatus] = useState([]);
  const [playbooks, setPlaybooks] = useState([]);
  const [jobInfo, setJobInfo] = useState(null);
  const [report, setReport] = useState(null);
  const [errors, setErrors] = useState([]);
  const [logjuicerUrl, setLogjuicerUrl] = useState("");
  const [logUrl, setLogUrl] = useState("");
  const [sourceMap, setSourceMap] = useState({});
  const [usage, setUsage] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const eventSourceRef = useRef(null);

  const addError = (e) => setErrors((prev) => [...prev, e]);

  async function getReport() {
    setStatus([]);
    setJobInfo(null);
    setPlaybooks([]);
    setReport(null);
    setErrors([]);
    setLogjuicerUrl("");
    setLogUrl("");
    setSourceMap({});
    setUsage(null);
    setIsLoading(true);

    if (!build) {
      setStatus(
        (_) => ["Build is missing, try adding ?build=... to the page url."],
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
        case "run_id":
          if (setID != null) {
            setID(body);
          }
          break;
        case "progress":
          setStatus((prevStatus) => [body, ...prevStatus]);
          break;
        case "report":
          setReport(body);
          break;
        case "logjuicer_url":
          setLogjuicerUrl(body);
          break;
        case "log_url":
          setLogUrl(body);
          break;
        case "source_map":
          setSourceMap(body);
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
      const arg = `?build=${encodeURIComponent(build)}` +
        (workflow ? `&workflow=${workflow}` : "");
      eventSource = new EventSource(`${backendUrl}/get${arg}`);

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
    return () => {};
  }, [build]);
  return (
    <div className="flex flex-col items-center">
      <div className="w-full max-w-4xl">
        <div
          className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-8"
          role="alert"
        >
          <p className="font-bold">
            <a
              href="https://github.com/RCAccelerator/rca-api"
              className="cursor-pointer hover:underline"
            >
              RCAv2 experiment
            </a>
          </p>
          <p>
            This box is powered by GenAI, the model can make mistakes, so
            double-check it
          </p>
        </div>
        <main className="w-full flex flex-col items-center gap-6">
          {isLoading && <Spinner />}
          {errors.length > 0 && (
            <div className="w-full bg-red-50 dark:bg-gray-800 border border-red-500 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-red-700 dark:text-red-400 border-b border-red-200 dark:border-gray-700 pb-2 mb-4">
                Error
              </h2>
              {errors.map((error, index) => (
                <pre
                  key={index}
                  className="text-red-600 dark:text-red-300 whitespace-pre-wrap break-words font-mono"
                >{error}</pre>
              ))}
            </div>
          )}
          {report && (
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
                <span className="font-semibold">Build URL:</span>
                <a
                  href={build}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline break-all"
                >
                  {build}
                </a>
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
              </div>
              {report.summary && (
                <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
                  <h3 className="font-semibold mb-2 text-blue-900 dark:text-blue-100">
                    Summary
                  </h3>
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
                      {report.summary}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
              {report.possible_root_causes &&
                report.possible_root_causes.length > 0 && (
                <>
                  {report.possible_root_causes.map((
                    rootCause,
                    rootCauseIndex,
                  ) => (
                    <div key={rootCauseIndex} className="mb-6">
                      <h3 className="font-semibold">
                        Possible Root Cause {rootCauseIndex + 1}
                      </h3>
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
                          {rootCause.cause}
                        </ReactMarkdown>
                      </div>
                      <h3 className="font-semibold pt-2">Evidences</h3>
                      <ul className="list-none p-0 m-0 font-mono text-sm space-y-2">
                        {rootCause.evidences.map((evidence, index) => (
                          <li key={index} className="pt-1 break-words">
                            <Evidence
                              error={evidence.error}
                              source={evidence.source}
                              log_url={logUrl}
                              source_map={sourceMap}
                              logjuicer_url={logjuicerUrl}
                            />
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </>
              )}
              {report.jira_tickets && report.jira_tickets.length > 0 && (
                <>
                  <h3 className="font-semibold pt-4">Related JIRA Tickets</h3>
                  <ul className="list-none p-0 m-0 space-y-2">
                    {report.jira_tickets.map((ticket, index) => (
                      <li key={index} className="pt-1">
                        <a
                          href={ticket.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 dark:text-blue-400 hover:underline break-all"
                        >
                          {ticket.key} - {ticket.summary}
                        </a>
                      </li>
                    ))}
                  </ul>
                </>
              )}
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
              {playbooks.length > 0 && (
                <>
                  <h3 className="font-semibold">Playbooks</h3>
                  <ul className="list-disc p-0 m-0 font-mono text-sm space-y-2 mb-3">
                    {playbooks.map((play, index) => (
                      <li key={index} className="pt-1 break-words">{play}</li>
                    ))}
                  </ul>
                </>
              )}
              {jobInfo && jobInfo.actions && (
                <>
                  <h3 className="font-semibold">Actions</h3>
                  <ul className="list-decimal p-0 ml-3 font-mono text-sm space-y-2">
                    {jobInfo.actions.map((action, index) => (
                      <li key={index} className="pt-1 break-words">{action}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
          {!isLoading && (status.length > 0) && (
            <div className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold border-b border-gray-200 dark:border-gray-700 pb-2 mb-4">
                Analysis Status
              </h2>
              <ul className="list-none p-0 m-0 font-mono text-sm space-y-2">
                {status.map((msg, index) => (
                  <li key={index} className="pt-1 break-words">{msg}</li>
                ))}
              </ul>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
