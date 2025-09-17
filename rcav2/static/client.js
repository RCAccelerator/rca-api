// Copyright © 2025 Red Hat
// SPDX-License-Identifier: Apache-2.0

function createReport(url) {

function debounce(func, delay) {
  let timeoutId;
  return function (...args) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      func.apply(this, args);
    }, delay);
  };
}
  const eventsList = document.getElementById("events");
  const reportContainer = document.getElementById("report-container");
  const messageArea = document.getElementById("message-area");

  let currentListItem;
  let llmOutputContainer;
  let currentMarkdown = "";

  function showMessage(message, type = "info") {
    messageArea.textContent = message;
    messageArea.classList.remove(
      "bg-blue-100",
      "text-blue-800",
      "bg-red-100",
      "text-red-800",
    );
    if (type === "info") {
      messageArea.classList.add("bg-blue-100", "text-blue-800");
    } else if (type === "error") {
      messageArea.classList.add("bg-red-100", "text-red-800");
    }
    messageArea.style.display = "block";
  }

  function showError(message) {
    const newElement = document.createElement("li");
    newElement.textContent = `Error: ${message}`;
    newElement.classList.add("text-red-800", "bg-red-100", "p-2", "rounded-md");
    eventsList.appendChild(newElement);
    currentListItem = null;
    llmOutputContainer = null;
  }


  function showChunk(chunk) {
    if (!currentListItem) {
      currentListItem = document.createElement("li");
      llmOutputContainer = document.createElement("div");
      llmOutputContainer.classList.add(
        "whitespace-pre-wrap",
        "bg-gray-50",
        "p-3",
        "rounded-md",
      );
      currentListItem.appendChild(llmOutputContainer);
      eventsList.appendChild(currentListItem);
      currentMarkdown = "";
    }
    currentMarkdown += chunk;
    llmOutputContainer.innerHTML = marked.parse(currentMarkdown);
  }
  const debouncedShowChunk = debounce(showChunk, 150);

  function showProgress(msg) {
    const newElement = document.createElement("li");
    newElement.textContent = msg;
    newElement.classList.add("font-semibold");
    eventsList.appendChild(newElement);
    currentListItem = null;
    llmOutputContainer = null;
  }

  function handleEvent(body, event) {
    if (event == "status") {
      if (body == "completed") {
        showMessage("Analysis complete.", "info");
      } else {
        showError(body);
      }
    } else if (event == "progress") {
      showProgress(body);
    } else if (event == "chunk") {
      debouncedShowChunk(body);
    }
  }

  function showCompleted(url) {
    showMessage("Build completed. Fetching report...", "info");
    fetch("/report?build=" + url)
      .then((resp) => {
        if (!resp.ok) {
          throw new Error(`Server responded with status ${resp.status}`);
        }
        return resp.json();
      })
      .then((report) => {
        eventsList.style.display = "none";
        for (const [event, body] of report) {
          handleEvent(body, event);
        }
        showMessage("Report loaded successfully.", "info");
      })
      .catch((err) => {
        console.error("Failed to fetch report:", err);
        showMessage(`Failed to fetch report: ${err.message}`, "error");
      });
  }

  if (!url) {
    showMessage(
      "No build URL provided. Add '?build=<URL>' to the page URL.",
      "error",
    );
  } else {
    try {
        new URL(url);
    } catch (error) {
        showMessage("The provided string is not a valid URL. Please enter a full URL (e.g., https://...).", "error");
        return;
    }

    showMessage("Submitting build for analysis...", "info");
    fetch("/submit?build=" + url, { method: "PUT" })
      .then((resp) => {
        if (!resp.ok) {
          throw new Error(`Server responded with status ${resp.status}`);
        }
        return resp.json();
      })
      .then((build) => {
        if (build.status === "PENDING") {
          showMessage("Build is pending. Streaming logs...", "info");
          eventsList.style.display = "block";
          reportContainer.innerHTML = "";

          const evtSource = new EventSource("/watch?build=" + url);
          evtSource.onmessage = (ev) => {
            const [event, body] = JSON.parse(ev.data);
            handleEvent(body, event);
            if (event == "status") {
              evtSource.close();
            } else if (event == "redirect") {
              evtSource.close();
              showCompleted(url);
            }
          };

          evtSource.onerror = (error) => {
            console.error("EventSource failed:", error);
            showMessage(
              "Error receiving build events. The connection was closed.",
              "error",
            );
            evtSource.close();
          };
        } else if (build.status === "COMPLETED") {
          showCompleted(url);
        } else {
          showMessage(`Unknown build status: ${build.status}`, "error");
        }
      })
      .catch((err) => {
        console.error("Failed to submit build:", err);
        showMessage(`Failed to submit build: ${err.message}`, "error");
      });
  }
}
