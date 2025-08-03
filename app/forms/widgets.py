from django.forms import RadioSelect


class ColorRadioSelect(RadioSelect):
    """
    一个自定义的颜色选择器组件 (Widget)。

    通过重写Django内置的 `RadioSelect` 组件的模板，将标准的单选按钮
    渲染为一组可点击的、带背景色的圆形色块，提供更直观的视觉选择体验。
    """
    template_name = 'app/widgets/color_radio/radio.html'
    option_template_name = 'app/widgets/color_radio/radio_option.html'