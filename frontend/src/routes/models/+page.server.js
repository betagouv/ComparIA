import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

export async function load() {
    // Chemin vers le fichier des modèles
    const modelsPath = resolve(process.cwd(), 'static/models.jsonl');

    try {
        // Lire le fichier ligne par ligne
        const fileContent = await readFile(modelsPath, 'utf-8');
        const models = fileContent.split('\n')
            .filter(line => line.trim() !== '')
            .map(line => JSON.parse(line))
            .map(model => ({
                ...model,
                url: `https://huggingface.co/${model.id}`
            }));

        return {
            models
        };
    } catch (error) {
        console.error('Error loading models:', error);
        return {
            models: []
        };
    }
}
