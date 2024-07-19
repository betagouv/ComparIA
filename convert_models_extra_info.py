import csv
import json
import re

def enrich_json(csv_file, json_file):
    with open(csv_file, 'r', encoding='utf-8') as csvfile, \
         open(json_file, 'r', encoding='utf-8') as jsonfile:

        reader = csv.DictReader(csvfile)
        data = json.load(jsonfile)

        for row in reader:
            model_name = row['Nom']

            if model_name in data:
                # Prioritize inferred information
                if 'open source ou propriétaire' in row and 'distribution' not in data[model_name]:
                    if row['open source ou propriétaire'] == 'open source':
                        data[model_name]['distribution'] = 'open-weights'
                    else:
                        data[model_name]['distribution'] = 'api-only'

                if 'famille' in row and 'family' not in data[model_name]:
                    data[model_name]['family'] = row['famille']

                if 'famille' in row and 'friendly_size' not in data[model_name]:
                    data[model_name]['friendly_size'] = row['famille']
                    if row['famille'] in ['XL', 'L', 'M', 'S']:
                        data[model_name]['intended_pool'] = row['famille']

                # Infer params and total_params from size field
                if 'taille' in row and 'params' not in data[model_name] and 'total_params' not in data[model_name]:
                    size_pattern = r'(\d+)([a-zA-Z]+)'
                    match = re.match(size_pattern, row['taille'])
                    if match:
                        size_value = int(match.group(1))
                        size_unit = match.group(2)
                        if size_unit == 'b':
                            data[model_name]['params'] = size_value * 1_000_000_000
                            data[model_name]['total_params'] = size_value * 1_000_000_000
                        elif size_unit == 'B':
                            data[model_name]['params'] = size_value
                            data[model_name]['total_params'] = size_value
                        elif 'x' in row['taille']:  # MoE model
                            moe_parts = row['taille'].split('x')
                            data[model_name]['params'] = int(moe_parts[0]) * 1_000_000_000
                            data[model_name]['total_params'] = int(moe_parts[1][:-1]) * 1_000_000_000

                # Append CSV data only if the field is not already present in JSON
                if 'description' in row and 'description' not in data[model_name]:
                    data[model_name]['description'] = row['description']
                if 'taille' in row and 'size' not in data[model_name]:
                    data[model_name]['size'] = row['taille']
                if 'paramètres' in row and 'parameters' not in data[model_name]:
                    data[model_name]['parameters'] = row['paramètres']
                if 'code source' in row and 'code_source' not in data[model_name]:
                    data[model_name]['code_source'] = row['code source']
                if 'corpus d\'entrainement' in row and 'training_dataset' not in data[model_name]:
                    data[model_name]['training_dataset'] = row['corpus d\'entrainement']
                if 'contexte' in row and 'context' not in data[model_name]:
                    data[model_name]['context'] = row['contexte']
                if 'ram systeme pour installation locale' in row and 'local_installation_ram' not in data[model_name]:
                    data[model_name]['local_installation_ram'] = row['ram systeme pour installation locale']
                if 'licence' in row and 'license' not in data[model_name]:
                    data[model_name]['license'] = row['licence']
                if 'régime' in row and 'regime' not in data[model_name]:
                    data[model_name]['regime'] = row['régime']
                if 'pool(s) envisagée(s)' in row and 'intended_use_cases' not in data[model_name]:
                    data[model_name]['intended_use_cases'] = row['pool(s) envisagée(s)']
                if 'date' in row and 'date' not in data[model_name]:
                    data[model_name]['date'] = row['date']
                if 'nombre de tokens (corpus)' in row and 'token_count' not in data[model_name]:
                    data[model_name]['token_count'] = row['nombre de tokens (corpus)']
                if 'knowledge cutoff' in row and 'knowledge_cutoff' not in data[model_name]:
                    data[model_name]['knowledge_cutoff'] = row['knowledge cutoff']
                if 'fourni via' in row and 'provided_via' not in data[model_name]:
                    data[model_name]['provided_via'] = row['fourni via']
                if 'remarques' in row and 'remarks' not in data[model_name]:
                    data[model_name]['remarks'] = row['remarques']
                if 'priorité intégration arène' in row and 'arena_integration_priority' not in data[model_name]:
                    data[model_name]['arena_integration_priority'] = row['priorité intégration arène']
                
                # Additional inferred fields based on provided example
                if 'Organisation' in row and 'organisation' not in data[model_name]:
                    data[model_name]['organisation'] = row['Organisation']
                if 'Conditions d\'usage' in row and 'conditions' not in data[model_name]:
                    data[model_name]['conditions'] = row['Conditions d\'usage']
                if 'Nom standard Hugging Face ou lien' in row and 'hugging_face_name_or_link' not in data[model_name]:
                    data[model_name]['hugging_face_name_or_link'] = row['Nom standard Hugging Face ou lien']

                # # Infer country from organisation if not present
                # if 'country' not in data[model_name]:
                #     organisation = row.get('Organisation', '').lower()
                #     if 'google' in organisation:
                #         data[model_name]['country'] = 'États-Unis'
                #     elif 'facebook' in organisation:
                #         data[model_name]['country'] = 'États-Unis'
                #     elif 'microsoft' in organisation:
                #         data[model_name]['country'] = 'États-Unis'
                #     elif 'baidu' in organisation:
                #         data[model_name]['country'] = 'Chine'
                #     # Add more rules as needed

                # Infer icon_path from organisation if not present
                # if 'icon_path' not in data[model_name]:
                #     organisation = row.get('Organisation', '').lower()
                #     if 'google' in organisation:
                #         data[model_name]['icon_path'] = 'google.png'
                #     elif 'facebook' in organisation:
                #         data[model_name]['icon_path'] = 'facebook.png'
                #     elif 'microsoft' in organisation:
                #         data[model_name]['icon_path'] = 'microsoft.png'
                #     elif 'baidu' in organisation:
                #         data[model_name]['icon_path'] = 'baidu.png'
                #     # Add more rules as needed

    with open(json_file, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile, indent=4, ensure_ascii=False)

# Example usage:
enrich_json('your_csv_file.csv', 'your_json_file.json')