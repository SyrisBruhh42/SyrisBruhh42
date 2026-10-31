import re

prompt = "Wearing a sculpted dark-titanium and gunmetal winged valkyrie crest helm piece with glowing emeraldfeather blades between her bronze horns, the companion lifts her chin with confident, heroic poise as her two glowing green eyes shine brightly in the clean studio light. She shifts her weight onto her front foot in a poised knightly readiness stance, gives a warm, reassuring nod as the dark-rimmed emerald crest feathers catch the light, and settles smoothly back into her starting pose. Locked static camera, clean solid white studio backdrop, no floating text or overlays. Audio: no speech; a crisp metallic latch click and soft breath in a dry studio with no background music."
regex = r"digital code|code streams|HUD|ISTP 5w6|enclave_07_willow|character\.png|A-pose|#FFFFFF|720x1280"

print("Regex match:", re.search(regex, prompt))
