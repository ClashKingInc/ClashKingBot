SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]

async def fetch(url, session):
    async with session.get(url) as response:
        return await response.json()

def create_superscript(num):
    digits = [int(num) for num in str(num)]
    new_num = ""
    for d in digits:
        new_num += SUPER_SCRIPTS[d]

    return new_num
