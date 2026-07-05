# End-to-end tests

This folder contains end-to-end tests for Presidio.
It requires the different services to be running as HTTP services.

Steps:
1. [Install presidio](https://presidio.dataprivacystack.org/installation/)
2. Run services, e.g., using `docker-compose`:
    ```sh
   docker-compose up --build -d 
   ```
   Note that these might take some time to build for the first time.
   
3. Install the e2e-tests framework, preferably in a virtual environment:
   ```sh
   pip install -r requirements.txt
   ```
4. Run tests:
   ```
   pytest
   ```

See more information on [Presidio's documentation on E2E tests](https://presidio.dataprivacystack.org/development/#end-to-end-tests).
