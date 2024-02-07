#!/bin/bash
celery -A trayapp worker -l INFO -B
