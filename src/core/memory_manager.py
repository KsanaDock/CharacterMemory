import uuid
from datetime import datetime
from typing import List, Dict
from src.models.schema import CharacterProfile, MemoryItem, SocialContext, Personality, Wealth, Health
from src.storage.json_store import JSONStore
from src.storage.vector_store import VectorStore
from src.services.llm_service import LLMService

class MemoryManager:
    def __init__(self, profile_path: str, vector_db_path: str, llm_service: LLMService):
        self.json_store = JSONStore(profile_path)
        self.vector_store = VectorStore(vector_db_path)
        self.llm_service = llm_service
        self.profile = self._load_or_create_profile()

    def _load_or_create_profile(self) -> CharacterProfile:
        data = self.json_store.load_profile()
        if data:
            return CharacterProfile(**data)
        else:
            # Default empty profile
            return CharacterProfile(
                name="New Character",
                context=SocialContext(world_view="", occupation="", current_location=""),
                personality=Personality(traits={}, values=[]),
                wealth=Wealth(),
                health=Health()
            )


    def update_memory(self, id: str, content: str, type: str, importance: int):
        self.vector_store.update_memory(id, content, type, importance)

    def delete_memory(self, id: str):
        self.vector_store.delete_memory(id)

    def retrieve_relevant_memories(self, query: str, n_results: int = 10) -> List[Dict]:
        return self.vector_store.search(query, n_results=n_results)

    def save_interaction(self, user_input: str, ai_response: str, user_name: str = "User"):
        user_mem = MemoryItem(
            id=str(uuid.uuid4()),
            type="observation",
            content=f"{user_name} said: {user_input}",
            importance=1
        )
        ai_mem = MemoryItem(
            id=str(uuid.uuid4()),
            type="action",
            content=f"I replied to {user_name}: {ai_response}",
            importance=1
        )
        self.vector_store.add_memories([user_mem, ai_mem])

    def chat(self, user_input: str) -> tuple[str, List[Dict]]:
        # 1. Retrieve relevant memories
        relevant_memories = self.retrieve_relevant_memories(user_input)
        context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])

        # 2. Construct System Prompt from Profile
        system_prompt = self._construct_system_prompt()

        # 3. Generate Response
        response = self.llm_service.generate_response(system_prompt, user_input, context_str)

        # 4. Store interaction
        self.save_interaction(user_input, response)

        return response, relevant_memories

    def _construct_system_prompt(self, user_name: str = "User", user_persona: str = "") -> str:
        p = self.profile
        return f"""You are {p.name}.
Context: {p.context.world_view}. You are a {p.context.occupation} at {p.context.current_location}.
Personality: {p.personality.traits}. Values: {p.personality.values}. Mood: {p.personality.mood}.
Status: Health {p.health.hp}, Wealth {p.wealth.currency}.

Interacting with: {user_name}
User Context: {user_persona}

Respond naturally based on your memory and current state."""

    def reflect_on_interaction(self, chat_history: List[Dict], user_name: str = "User") -> str:
        """
        Analyzes the chat history to update the character's profile (mood, relationships, daily log).
        """
        if not chat_history:
            return "No interaction to reflect on."

        # 1. Prepare Context
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
        current_profile = self.profile.model_dump_json()
        
        # 2. Construct Prompt
        prompt = f"""
        Analyze the following interaction history and the current character profile. 
        The user's name is '{user_name}'.
        Determine if any updates are needed for the character's internal state.
        
        Current Profile (JSON):
        {current_profile}
        
        Interaction History:
        {history_str}
        
        Instructions:
        1. Summarize the interaction into a 'Daily Log Entry'.
        2. Update 'Mood' if changed.
        3. Update 'Relationships' (create new or update existing affinity/history) if relevant.
        4. **Check for Learning**: Did the character learn a new skill or improve an existing one?
        5. **Check for Growth**: Did the character's personality traits or values change?
        6. **Check for Life Changes**: Did the character's occupation or location change?
        
        Return ONLY a valid JSON object with the following structure (do not include markdown formatting):
        
        {{
            "daily_log": {{ "activity": "...", "interacted_with": ["..."] }},
            "mood": "...",
            "relationships": {{
                "Target Name": {{ "affinity": 0, "tags": [], "history": ["..."] }}
            }},
            "skills_update": [
                {{ "name": "Skill Name", "level": 1, "description": "..." }}
            ],
            "personality_update": {{
                "traits": {{ "Trait Name": 5 }},
                "values": ["Value 1", "Value 2"]
            }},
            "context_update": {{
                "occupation": "...",
                "current_location": "..."
            }}
        }}
        """
        
        # 3. Call LLM
        response = self.llm_service.generate_response("You are a backend system that manages character state. Output only JSON.", prompt)
        
        # 4. Parse and Apply Updates
        try:
            import json
            # Clean response if it contains markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            data = json.loads(response.strip())
            
            updates = []
            
            # Update Daily Log
            if "daily_log" in data:
                from src.models.schema import DailyLogEntry
                log_entry = DailyLogEntry(
                    activity=data["daily_log"]["activity"],
                    interacted_with=data["daily_log"].get("interacted_with", [])
                )
                self.profile.daily_log.append(log_entry)
                
                # ALSO save to Vector Store for RAG
                log_memory = MemoryItem(
                    id=str(uuid.uuid4()),
                    type="daily_log",
                    content=f"Daily Log ({datetime.now().strftime('%Y-%m-%d')}): {log_entry.activity}. Interacted with: {', '.join(log_entry.interacted_with)}",
                    importance=8, # High importance for daily summaries
                    summary=log_entry.activity # Use activity as summary
                )
                self.vector_store.add_memories([log_memory])
                
                updates.append("Added daily log entry (and saved to long-term memory).")
                
            # Update Mood
            if "mood" in data and data["mood"] != self.profile.personality.mood:
                old_mood = self.profile.personality.mood
                self.profile.personality.mood = data["mood"]
                updates.append(f"Mood changed from {old_mood} to {data['mood']}.")
                
            # Update Relationships
            if "relationships" in data:
                from src.models.schema import Relationship
                for name, rel_data in data["relationships"].items():
                    if name not in self.profile.relationships:
                        self.profile.relationships[name] = Relationship(target_name=name)
                        updates.append(f"New relationship with {name}.")
                    
                    rel = self.profile.relationships[name]
                    if "affinity" in rel_data:
                        rel.affinity = rel_data["affinity"]
                    if "tags" in rel_data:
                        rel.tags = rel_data["tags"]
                    if "history" in rel_data:
                        rel.history.extend(rel_data["history"])

            # Update Skills
            if "skills_update" in data and data["skills_update"]:
                from src.models.schema import Skill
                for skill_data in data["skills_update"]:
                    # Check if skill exists
                    existing_skill = next((s for s in self.profile.skills if s.name == skill_data["name"]), None)
                    if existing_skill:
                        existing_skill.level = skill_data["level"]
                        existing_skill.description = skill_data["description"]
                        updates.append(f"Updated skill {skill_data['name']} to level {skill_data['level']}.")
                    else:
                        new_skill = Skill(
                            name=skill_data["name"],
                            level=skill_data["level"],
                            description=skill_data["description"]
                        )
                        self.profile.skills.append(new_skill)
                        updates.append(f"Learned new skill: {skill_data['name']}.")

            # Update Personality
            if "personality_update" in data:
                p_update = data["personality_update"]
                if "traits" in p_update:
                    self.profile.personality.traits.update(p_update["traits"])
                    updates.append("Updated personality traits.")
                if "values" in p_update:
                    # Merge values uniquely
                    current_values = set(self.profile.personality.values)
                    new_values = set(p_update["values"])
                    self.profile.personality.values = list(current_values.union(new_values))
                    updates.append("Updated values.")

            # Update Context
            if "context_update" in data:
                c_update = data["context_update"]
                if "occupation" in c_update and c_update["occupation"]:
                    self.profile.context.occupation = c_update["occupation"]
                    updates.append(f"Occupation changed to {c_update['occupation']}.")
                if "current_location" in c_update and c_update["current_location"]:
                    self.profile.context.current_location = c_update["current_location"]
                    updates.append(f"Moved to {c_update['current_location']}.")
                        
            self.save_profile()
            return "\n".join(updates) if updates else "No significant changes."
            
        except Exception as e:
            return f"Failed to process reflection: {str(e)}\nRaw Response: {response}"
    
    def save_profile(self):
        self.json_store.save_profile(self.profile)