from util import file_system as fs

class Session():
    conversation:list[dict]
    preset:str = ""
    index:int = 0      
    
    def __init__(self, model: str, preset: str):
        self.model = model
        self.preset = preset
        self.conversation = [{"role": "system", "content": self.preset}]  
    
    def new_message(self, role:str):
        self.index += 1
        self.conversation.append({"role": role, "content": []})
    
    def add_text(self, text:str):
        self.conversation[self.index]["content"].append({"type": "text", "text": text})

    def add_image(self, url:str):
        local_url = fs.save_file(url)
        base64_image = fs.read_file_as_base64(local_url)
        self.conversation[self.index]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
        fs.remove_file(local_url)

    def get_conversation(self) -> list[dict]:
        return self.conversation
    
    def clear_conversation(self):
        self.index = 0
        self.conversation = [{"role": "system", "content": self.preset}]

    def clear_oldest_message(self):
        if(self.index > 0):
            self.conversation.remove(self.conversation[1])
            self.index -= 1 
    
    def change_preset(self, preset:str):
        self.preset = preset
        self.conversation[0]["content"] = self.preset
    
    def get_model(self):
        return self.model
    
    def set_model(self, model:str):
        self.model = model