from flask import Flask, request, jsonify, render_template
from get_clinical_trials_from_qdrant import get_clinical_trials

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        results = get_clinical_trials(query, n_results = 10)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 