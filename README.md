## Setup
1. **Install deps**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
2. **Environment**: set via `.env` or your shell (validated by Pydantic on import)
   ```env
   CUSTOM_SEARCH_API_KEY=your_google_custom_search_api_key
   CUSTOM_SEARCH_ENGINE_ID=your_search_engine_id
   OPENAI_API_KEY=your_openai_key
   ```
3. **Lint**:
  ```
  # Lint
  ruff check src

  # Auto-fix + format
  ruff check src --fix
  ruff format src
  black src
  # OR
  ./lint.sh
  ```

4. **Running**:
  ```
  python -m src.main "Did Ada Lovelace write the first algorithm?"
  ```

5. **Testing**:
  ```
  pytest # all tests

  pytest <test_path(s)> # specific test
  ```