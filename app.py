from flask import Flask, request, jsonify, render_template
from query_clinical_trials import get_clinical_trials
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# for local runs, first start with `docker run -p 6333:6333 qdrant/qdrant`
@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        results = get_clinical_trials(query, n_results = 10)
        
        # Process the lat_lon field to ensure proper JSON serialization
        for result in results:
            if 'lat_lon' in result:
                # lat_lon is already a string representation of a list from the query_clinical_trials.py
                # We don't need to modify it since our JavaScript will parse it
                pass
            else:
                # If lat_lon isn't in the result, add an empty array
                result['lat_lon'] = '[]'
                
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)