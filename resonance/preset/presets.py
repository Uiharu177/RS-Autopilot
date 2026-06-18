import time

from loguru import logger

from resonance.device.device import input_tap, screenshot
from resonance.preset.control import click_image
from resonance.utils.utils import RESOURCES_PATH
from resonance.vision.color import BGR

FIGHT_TIME = 1000


def go_shop():
    click_image(RESOURCES_PATH / "shop" / "1.png", trynum=1, check_err=False)


def wait_fight_end():
    logger.info("等待战斗结束")
    start = time.perf_counter()
    while time.perf_counter() - start < FIGHT_TIME:
        image = screenshot()
        bgrs = image.get_bgrs([(1114, 630), (1204, 624), (167, 29)])
        logger.debug(f"等待战斗结束颜色检查: {bgrs}")
        if (
            BGR(198, 200, 200) <= bgrs[0] <= BGR(202, 204, 204) 
            and BGR(183, 185, 185) <= bgrs[1] <= BGR(187, 189, 189)
        ):
            logger.info("检测到执照等级提升")
            input_tap((1151, 626))
            continue
        elif image.crop_image((1070, 600), (1251, 670)).match_template(
            RESOURCES_PATH / "fight/end_fight.png", 0.995
        ):
            logger.info("战斗结束")
            time.sleep(1.0)
            input_tap((1151, 626))
            return True
        elif bgrs[2] == [124, 126, 125]:
            logger.info("开启自动战斗")
            input_tap((233, 44))
        time.sleep(3)
    logger.error("战斗超时")
    return False
