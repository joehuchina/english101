"""Bad sentences that check.py must reject. Run: .venv/bin/python test_check.py"""
from check import Lexicon, check_scene

LEX = Lexicon()
UNIT = {"scene_id": "T-1", "level": "A1", "topics": "daily",
        "targets": ["bedroom", "juice", "table", "fine", "milk", "morning"]}


def s(en, zh="这是一个用来测试的中文句子"):
    return {"en": en, "zh": zh}


GOOD = [
    s("My sister drinks orange juice in her bedroom.", "我妹妹在她的卧室里喝橙汁。"),
    s("Dad puts the milk on the kitchen table.", "爸爸把牛奶放在厨房的桌子上。"),
    s("It is a fine and sunny morning today.", "今天是一个晴朗的好早晨。"),
]

BAD = {
    "missing target": [
        s("My brother sleeps in a small room.", "我弟弟睡在一个小房间里。"),
        s("We eat apples with our friends at home.", "我们和朋友在家吃苹果。"),
    ],
    "wrong part of speech": [
        s("The teachers table the new plan every day.", "老师们每天都搁置新计划。"),
        s("The police fine the drivers on this road.", "警察对这条路上的司机罚款。"),
    ],
    "above level": [
        s("The juice was inherently prohibitive and meddlesome.", "这果汁本质上贵得离谱又多事。"),
        s("A cohesive threshold surrounds the bedroom.", "一道紧密的门槛围绕着卧室。"),
    ],
    "too long": [
        s("Every morning my little brother and I drink a big glass of cold milk in the kitchen.",
          "每天早上我和弟弟都在厨房里喝一大杯冷牛奶。"),
        s("In the bedroom there is a table, two chairs, a bed, a lamp and a big window.",
          "卧室里有一张桌子、两把椅子、一张床、一盏灯和一扇大窗户。"),
    ],
    "duplicate": [
        s("My sister drinks orange juice in her bedroom.", "我妹妹在她卧室里喝橙汁。"),
        s("Dad puts the milk on the kitchen table now.", "爸爸现在把牛奶放在厨房桌上。"),
    ],
}


def run():
    scene = {"scene_id": "T-1", "sentences": GOOD}
    res = check_scene(scene, UNIT, LEX)
    for r in res["sentences"]:
        assert not r["problems"], (GOOD[r["i"]]["en"], r["problems"])
    assert res["missing"] == [], res["missing"]
    print("good sentences pass, all 6 targets found")

    seen = [g["en"] for g in GOOD]
    for kind, sents in BAD.items():
        for bad in sents:
            r = check_scene({"scene_id": "T-1", "sentences": [bad]}, UNIT, LEX,
                            seen=seen if kind == "duplicate" else ())
            sr = r["sentences"][0]
            if kind in ("missing target", "wrong part of speech"):
                caught = not sr["hits"] or (kind == "wrong part of speech" and
                                            not {"table", "fine"} & set(sr["hits"]))
            else:
                caught = bool(sr["problems"])
            print(f"{'caught' if caught else 'MISSED'}  {kind:22s} {bad['en']}  {sr['problems']} hits={sr['hits']}")
            assert caught


if __name__ == "__main__":
    run()
