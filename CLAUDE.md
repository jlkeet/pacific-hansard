# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Install dependencies: `pip install -r requirements.txt`
- Run converters: `python scripts/[country]/[country]-hansard-converter.py`
- Start containers: `docker-compose up -d`
- Stop containers: `docker-compose down`
- Access web interface: http://localhost:8080

## Code Style
- Use Python 3.9+ standard style (PEP 8)
- Indentation: 4 spaces
- Imports: standard library first, then third-party, then local modules
- Error handling: Use try/except with specific exceptions
- Naming: snake_case for functions/variables, CamelCase for classes
- String formatting: Use f-strings
- Documentation: Include docstrings for functions/classes
- Logging: Use Python's logging module instead of print statements

## Project Structure
- Country-specific code in /scripts/[country]/
- Web interface in /site/
- Docker configuration for deployment
- HTML parsing using BeautifulSoup
- Database: MySQL with documents indexed in Solr