@echo off
cd /d "%~dp0"
if not exist instance\outbox mkdir instance\outbox
start explorer instance\outbox
