import json

from quart import Quart

app = Quart(__name__)

@app.post('/api/2.1/unity-catalog/temporary-table-credentials')
def temporary_table_credentials():
    return {
        "aws_temp_credentials": json.load(open('creds.json'))
    }

if __name__ == '__main__':
    app.run(port=8080)