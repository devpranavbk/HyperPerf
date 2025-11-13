import sys
import json
def generate_artillery_yaml(api_file, output_file, target=None, duration=30, arrival_rate=2):
    with open(api_file, 'r') as f:
        apis = json.load(f)
    # If the input is a list of dicts (with method/url/post_data), handle accordingly
    if isinstance(apis, list) and isinstance(apis[0], dict):
        # Try to extract a common target from the first URL
        if not target:
            from urllib.parse import urlparse
            first_url = apis[0]['url']
            parsed = urlparse(first_url)
            target = f"{parsed.scheme}://{parsed.netloc}"
        flows = []
        for api in apis:
            path = urlparse(api['url']).path
            method = api.get('method', 'GET').upper()
            if method == 'POST':
                flows.append({'post': {'url': path, 'json': json.loads(api.get('post_data', '{}'))}})
            else:
                flows.append({'get': {'url': path}})
    else:
        raise ValueError('Input JSON must be a list of dicts with url/method/post_data')
    # Build YAML
    import yaml
    artillery_config = {
        'config': {
            'target': target,
            'phases': [
                {'duration': duration, 'arrivalRate': arrival_rate}
            ]
        },
        'scenarios': [
            {'flow': flows}
        ]
    }
    with open(output_file, 'w') as f:
        yaml.dump(artillery_config, f, sort_keys=False)
    print(f"Artillery script written to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_artillery_yaml.py <api_file> <output_file> [duration] [arrival_rate]")
        sys.exit(1)
    api_file = sys.argv[1]
    output_file = sys.argv[2]
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    arrival_rate = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    generate_artillery_yaml(api_file, output_file, duration=duration, arrival_rate=arrival_rate)
