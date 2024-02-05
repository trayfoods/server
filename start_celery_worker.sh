#!/bin/bash
celery -A trayapp worker --loglevel=info
