import streamlit as st
import ollama
from duckduckgo_search import DDGS

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Chatbot avec Accès Web",
    page_icon="🌐"
)

# --- Constantes ---
# Assurez-vous que ce modèle est bien téléchargé via `ollama pull llama3`
OLLAMA_MODEL = 'gemma3n' 

# --- Fonctions Utilitaires ---

def search_the_web(query):
    """Effectue une recherche web et retourne les résultats formatés."""
    st.write(f"Recherche sur le web pour : '{query}'...")
    try:
        with DDGS() as ddgs:
            # max_results=4 pour ne pas surcharger le contexte
            results = list(ddgs.text(query, max_results=4))
            if not results:
                st.warning("Aucun résultat trouvé sur le web.")
                return "Aucune information trouvée sur le web."

            # Formatte les résultats pour les injecter dans le prompt
            context = "Informations trouvées sur le web :\n\n"
            for i, result in enumerate(results):
                context += f"Source {i+1}: {result['title']}\n"
                context += f"Extrait: {result['body']}\n"
                context += f"URL: {result['href']}\n\n"
            
            return context
    except Exception as e:
        st.error(f"Erreur lors de la recherche web : {e}")
        return "Erreur lors de la récupération d'informations sur le web."

# --- Interface Streamlit ---

st.title("🤖 Chatbot Augmenté par le Web")
st.caption(f"Utilise le modèle `{OLLAMA_MODEL}` via Ollama")

st.info("Posez une question sur un événement récent, une personnalité ou un sujet d'actualité. L'assistant cherchera sur le web avant de vous répondre.")

# Initialisation de l'historique de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrée utilisateur
if prompt := st.chat_input("Quelle est votre question ?"):
    # Ajouter le message de l'utilisateur à l'historique et l'afficher
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Lancer le processus de réponse de l'assistant
    with st.chat_message("assistant"):
        # 1. Effectuer la recherche web
        web_context = search_the_web(prompt)
        
        # 2. Construire le prompt augmenté
        system_prompt = f"""
        Tu es un assistant expert et utile. Ta tâche est de répondre à la question de l'utilisateur.
        Utilise les informations suivantes, extraites du web, pour construire ta réponse.
        Cite tes sources en ajoutant les URLs à la fin de ta réponse si possible.
        Sois concis et direct.

        --- CONTEXTE WEB ---
        {web_context}
        --- FIN DU CONTEXTE ---
        """

        # 3. Envoyer le tout à Ollama en mode streaming
        with st.spinner("L'assistant réfléchit..."):
            # On crée un message système temporaire + le message utilisateur
            api_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # Fonction générateur pour extraire le contenu des chunks Ollama
            def response_generator():
                response_stream = ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=api_messages,
                    stream=True
                )
                for chunk in response_stream:
                    if hasattr(chunk, 'message') and chunk.message.content:
                        yield chunk.message.content
                    elif isinstance(chunk, dict) and chunk.get('message', {}).get('content'):
                        yield chunk['message']['content']
            
            # Utilisation de st.write_stream avec le générateur corrigé
            full_response = st.write_stream(response_generator())

    # 4. Ajouter la réponse complète de l'assistant à l'historique
    st.session_state.messages.append({"role": "assistant", "content": full_response})