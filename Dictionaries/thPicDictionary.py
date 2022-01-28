

def thDictionary(thLevel):
    switcher = {
        5: "https://cdn.discordapp.com/attachments/842820614163398698/861379024420601866/5.png",
        6: "https://cdn.discordapp.com/attachments/842820614163398698/861379445498970122/6.png",
        7: "https://cdn.discordapp.com/attachments/842820614163398698/861379443053035530/7.png",
        8: "https://cdn.discordapp.com/attachments/842820614163398698/861379439903768586/8.png",
        9: "https://cdn.discordapp.com/attachments/842820614163398698/861379437843972106/9.png",
        10: "https://cdn.discordapp.com/attachments/842820614163398698/861379434543710248/10.png",
        11: "https://cdn.discordapp.com/attachments/842820614163398698/861379432995094538/11.png",
        12: "https://cdn.discordapp.com/attachments/842820614163398698/861379431415283732/12.5.png",
        13: "https://cdn.discordapp.com/attachments/842820614163398698/861379429653545000/13.5.png",
        14: "https://cdn.discordapp.com/attachments/842820614163398698/861379428214636554/14.5.png"
    }

    pic = switcher.get(thLevel, "No Picture Found")
    return pic
