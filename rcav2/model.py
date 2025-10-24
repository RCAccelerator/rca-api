# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import dspy  # type: ignore[import-untyped]
from dspy.utils.callback import BaseCallback  # type: ignore[import-untyped]
import os

import opik
from opik.integrations.dspy.callback import OpikCallback
from rcav2.config import OPIK_PROJECT_NAME


def get_lm(name: str, max_tokens: int) -> dspy.LM:
    return dspy.LM(
        f"gemini/{name}",
        temperature=0.5,
        max_tokens=max_tokens,
        api_key=os.environ["LLM_GEMINI_KEY"],
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


def init_dspy() -> None:
    dspy.settings.configure(track_usage=True)

    # Check if Opik is explicitly disabled
    if os.environ.get("OPIK_DISABLED", "false").lower() == "true":
        print("Opik integration disabled by OPIK_DISABLED environment variable")
        callbacks = []  # type: ignore
        if os.environ.get("DSPY_DEBUG"):
            callbacks.append(AgentLoggingCallback())
        dspy.configure(lm=get_lm("gemini-2.5-pro", 1024 * 1024), callbacks=callbacks)
        return

    # Configure Opik - use local deployment by default
    try:
        print("Configuring Opik for local deployment")
        opik.configure(use_local=True)

        opik_callback = OpikCallback(
            project_name=OPIK_PROJECT_NAME,
            log_graph=True,
        )
        dspy.configure(
            lm=get_lm("gemini-2.5-pro", 1024 * 1024), callbacks=[opik_callback]
        )
        print(f"DSPy configured with Opik tracing (project: {OPIK_PROJECT_NAME})")
    except Exception as e:
        print(f"Failed to configure Opik: {e}")
        print("Falling back to DSPy without Opik tracing")
        dspy.configure(lm=get_lm("gemini-2.5-pro", 1024 * 1024))


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
