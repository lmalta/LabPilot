import "dotenv/config";

export const OLLAMA_URL =
  process.env.OLLAMA_URL ?? "<ADRESSE_OLLAMA>";

export const OLLAMA_MODEL =
  process.env.OLLAMA_MODEL ?? "<MODELE_OLLAMA>";
