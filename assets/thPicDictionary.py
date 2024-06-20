def thDictionary(thLevel):
    switcher = {
        1: 'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-1.png?raw=true',
        2: 'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-2.png?raw=true',
        3: 'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-3.png?raw=true',
        4: 'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-4.png?raw=true',
        5: 'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-5.png?raw=true',
        6: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}.png?raw=true',
        7: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}.png?raw=true',
        8: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}.png?raw=true',
        9: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}.png?raw=true',
        10: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}.png?raw=true',
        11: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}.png?raw=true',
        12: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}.png?raw=true',
        13: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}-2.png?raw=true',
        14: f'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-{thLevel}-2.png?raw=true',
        15: 'https://github.com/MagicTheDev/ClashKing/blob/master/Assets/th_pics/town-hall-15-2.png?raw=true',
        16: 'https://cdn.clashking.xyz/clash-assets/townhalls/16.png',
    }

    return switcher.get(thLevel, 'No Picture Found')
