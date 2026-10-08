import { request } from "node:http";
import { OLLAMA_MODEL, OLLAMA_URL } from "./configuration.js";
import { definitionsOutils } from "./labpilot.js";
import type {
  Message,
  MessageAssistant,
  MessageTool,
  ToolCall,
  ToolDefinition,
  ToolExecution,
} from "./types.js";

interface ReponseOllama {
  message: MessageAssistant;
}

interface RequeteOllama {
  model: string;
  messages: Message[];
  tools: ToolDefinition[];
  stream: false;
  think: false;
}

export class OllamaClient {
  public async chat(
    messages: Message[],
  ): Promise<MessageAssistant> {
    const payload: RequeteOllama = {
      model: OLLAMA_MODEL,
      messages,
      tools: definitionsOutils,
      stream: false,
      think: false,
    };

    const url = new URL("/api/chat", OLLAMA_URL);

    const reponse = await new Promise<string>(
      (resoudre, rejeter) => {
        const requete = request(
          url,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          },
          (reponseHttp) => {
            let donnees = "";

            reponseHttp.setEncoding("utf8");

            reponseHttp.on("data", (morceau) => {
              donnees += morceau;
            });

            reponseHttp.on("end", () => {
              if (
                reponseHttp.statusCode === undefined ||
                reponseHttp.statusCode < 200 ||
                reponseHttp.statusCode >= 300
              ) {
                rejeter(
                  new Error(
                    `Ollama a retourné le code HTTP ${reponseHttp.statusCode}.`,
                  ),
                );
                return;
              }

              resoudre(donnees);
            });
          },
        );

        requete.on("error", rejeter);

        requete.write(JSON.stringify(payload));
        requete.end();
      },
    );

    const resultat = JSON.parse(reponse) as ReponseOllama;

    return resultat.message;
  }
}

export function convertirToolCallEnExecution(
  appel: ToolCall,
): ToolExecution {
  return {
    name: appel.function.name,
    arguments: appel.function.arguments,
  };
}

export function convertirResultatEnMessageOutil(
  nomOutil: string,
  resultat: unknown,
): MessageTool {
  return {
    role: "tool",
    content: JSON.stringify(resultat),
    tool_name: nomOutil,
  };
}
