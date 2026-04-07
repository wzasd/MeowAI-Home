from src.utils.config import get_cat_config


class OrangeConfig:
    def __init__(self):
        config = get_cat_config("阿橘")
        self.name = config["name"]
        self.model = config["model"]
        self.provider = config["provider"]
        self.role = config["role"]
        self.personality = config["personality"]
        self.specialties = config["specialties"]
        self.catchphrases = config["catchphrases"]
