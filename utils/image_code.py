import random
import string
from PIL import Image, ImageDraw, ImageFilter, ImageFont


class FontNotFound(Exception):
    """当指定的字体文件无法找到时引发的自定义异常。"""
    pass


def generate_verification_code(width=120, height=30, char_length=5, font_file='kumo.ttf', font_size=28):
    """
    生成一个带有随机字符和干扰元素的图像验证码。

    Args:
        width (int): 图像的宽度（像素）。
        height (int): 图像的高度（像素）。
        char_length (int): 验证码中的字符数量。
        font_file (str): 用于渲染字符的 .ttf 字体文件的路径。
        font_size (int): 字体大小。

    Returns:
        tuple: 一个包含 Pillow 图像对象和验证码字符串的元组。

    Raises:
        FontNotFound: 如果指定的字体文件无法找到。
    """

    # 1. 创建一个白色的空白图像
    image = Image.new(mode='RGB', size=(width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    def get_random_char():
        """从所有大写字母中随机选择一个。"""
        return random.choice(string.ascii_uppercase)

    def get_random_color():
        """生成一个随机的亮色，以确保在白色背景上可见。"""
        return (random.randint(0, 255), random.randint(10, 255), random.randint(64, 255))

    # 2. 加载字体文件，如果找不到则引发自定义异常
    try:
        font = ImageFont.truetype(font_file, font_size)
    except IOError:
        raise FontNotFound(f"字体文件 '{font_file}' 未找到或无法读取。请确保文件路径正确。")

    # 3. 在图像上绘制验证码字符
    code_chars = []
    for i in range(char_length):
        char = get_random_char()
        code_chars.append(char)
        x_pos = i * (width / char_length) + random.uniform(-2, 2)  # 添加水平抖动
        y_pos = random.randint(0, 4)  # 轻微的垂直抖动
        draw.text(xy=(x_pos, y_pos), text=char, font=font, fill=get_random_color())

    # 4. 添加干扰元素以增加识别难度
    # 绘制干扰点
    for _ in range(80):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point(xy=(x, y), fill=get_random_color())

    # 绘制干扰线
    for _ in range(5):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line(xy=((x1, y1), (x2, y2)), fill=get_random_color())

    # 5. 应用滤镜使图像更模糊，进一步增强安全性
    image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)

    code_string = "".join(code_chars)
    return image, code_string