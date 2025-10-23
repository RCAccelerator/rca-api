# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
A standalone FastApi, used by the `make serve` rule.
"""

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI

import rcav2.api

app = FastAPI(lifespan=rcav2.api.lifespan)
rcav2.api.setup_handlers(app)
app.mount("/", StaticFiles(directory="dist", html=True), name="static")
