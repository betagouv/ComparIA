import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
  const PUBLIC_API_URL = process.env.PUBLIC_API_URL;
  try {
    const response = await fetch(`${PUBLIC_API_URL}/available_models`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const models = await response.json();
    return {
      models
    };
  } catch (error) {
    console.error("Failed to fetch models:", error);
    return {
      models: []
    };
  }
};
