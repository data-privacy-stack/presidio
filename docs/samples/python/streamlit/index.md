# Simple demo website for Presidio
Here's a simple app, written in pure Python, to create a demo website for Presidio.
The app is based on the [streamlit](https://streamlit.io/) package.

A live version can be found here: https://huggingface.co/spaces/presidio/presidio_demo

## Requirements
1. Clone the repo and move to the `docs/samples/python/streamlit` folder
2. Install dependencies (preferably in a virtual environment)

```sh
pip install -r requirements.txt
```
> Note: This would install additional packages such as `transformers` and `flair` which are not mandatory for using Presidio.

3. *Optional*: Update the `analyzer_engine` and `anonymizer_engine` functions for your specific implementation (in `presidio_helpers.py`).
4. Start the app:

```sh
streamlit run presidio_streamlit.py
```

5. Consider adding an `.env` file with the following environment variables, for further customizability:
```sh
TA_KEY=YOUR_TEXT_ANALYTICS_KEY
TA_ENDPOINT=YOUR_TEXT_ANALYTICS_ENDPOINT
OPENAI_TYPE="Azure" #or "openai"
OPENAI_KEY=YOUR_OPENAI_KEY
OPENAI_API_VERSION = "2023-05-15"
AZURE_OPENAI_ENDPOINT=YOUR_AZURE_OPENAI_AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT=text-davinci-003
ALLOW_OTHER_MODELS=true #true if the user could download new models
```
## Output
Output should be similar to this screenshot:
![image](https://github.com/data-privacy-stack/presidio/assets/3776619/7d0eadf1-e750-4747-8b59-8203aa43cac8)
