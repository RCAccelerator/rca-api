# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the model configuration.
"""

import os

# Workaround https://github.com/stanfordnlp/dspy/issues/8717
if not os.path.exists(os.path.expanduser("~/")):
    os.environ["DISK_CACHE_DIR"] = "/tmp/.dspy_cache"

import dspy  # type: ignore[import-untyped]
from dspy.utils.callback import BaseCallback  # type: ignore[import-untyped]
import opik
from opik.integrations.dspy.callback import OpikCallback

from rcav2.config import Settings
from rcav2.env import Env


class TraceManager:
    def __init__(self, env: Env, run_id: str, workflow: str, url: str):
        if env.settings.OPIK_DISABLED:
            self.enabled = False
        else:
            self.enabled = True
            build_id = url.split("/")[-1] if "/" in url else "unknown"
            trace_name = f"RCA {workflow.title()} - Build {build_id}"
            metadata = {
                "build_url": url,
                "build_id": build_id,
                "run_id": run_id,
                "workflow_type": workflow,
            }
            tags = [env.settings.OPIK_PROJECT_NAME, workflow] + env.settings.OPIK_TAGS
            self.manager = opik.start_as_current_trace(
                trace_name,
                metadata=metadata,
                tags=tags,
                project_name=env.settings.OPIK_PROJECT_NAME,
            )

    def __enter__(self):
        if self.enabled:
            return self.manager.__enter__()
        return None

    def __exit__(self, *args):
        if self.enabled:
            return self.manager.__exit__(*args)
        return False


def get_lm(settings: Settings, name: str, max_tokens: int) -> dspy.LM:
    return dspy.LM(
        f"gemini/{name}",
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=max_tokens,
        api_key=settings.LLM_GEMINI_KEY,
    )


# From: https://dspy.ai/tutorials/observability/?h=callback#building-a-custom-logging-solution
# 1. Define a custom callback class that extends BaseCallback class
class AgentLoggingCallback(BaseCallback):
    # 2. Implement on_module_end handler to run a custom logging code.
    def on_module_end(self, call_id, outputs, exception):
        step = "Reasoning" if self._is_reasoning_output(outputs) else "Acting"
        print(f"== {step} Step ===")
        for k, v in outputs.items():
            print(f"  {k}: {v}")
        print("\n")

    def _is_reasoning_output(self, outputs):
        return any(k.startswith("Thought") for k in outputs.keys())


def init_dspy(settings: Settings) -> None:
    dspy.settings.configure(track_usage=True)

    # Check if Opik is explicitly disabled
    if settings.OPIK_DISABLED:
        print("Opik integration disabled by OPIK_DISABLED environment variable")
        callbacks = []  # type: ignore
        if settings.DSPY_DEBUG:
            callbacks.append(AgentLoggingCallback())
        dspy.configure(
            lm=get_lm(settings, "gemini-2.5-pro", 1024 * 1024),
            callbacks=callbacks,
        )
        return

    # Configure Opik - use local deployment by default
    try:
        print("Configuring Opik")

        opik_callback = OpikCallback(
            project_name=settings.OPIK_PROJECT_NAME,
            log_graph=True,
        )
        dspy.configure(
            lm=get_lm(settings, "gemini-2.5-pro", 1024 * 1024),
            callbacks=[opik_callback],
        )
        print(
            f"DSPy configured with Opik tracing (project: {settings.OPIK_PROJECT_NAME})"
        )
    except Exception as e:
        print(f"Failed to configure Opik: {e}")
        print("Falling back to DSPy without Opik tracing")
        dspy.configure(lm=get_lm(settings, "gemini-2.5-pro", 1024 * 1024))


async def emit_dspy_usage(result, worker):
    usages = result.get_lm_usage()
    if usages:
        for model, usage in usages.items():
            await worker.emit(
                dict(
                    model=model,
                    input=usage.get("prompt_tokens"),
                    output=usage.get("completion_tokens"),
                ),
                event="usage",
            )
