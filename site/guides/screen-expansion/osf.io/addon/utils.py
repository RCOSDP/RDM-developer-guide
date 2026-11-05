# -*- coding: utf-8 -*-

# widget: ここから
def serialize_myscreen_widget(node):
    myscreen = node.get_addon('myscreen')
    ret = {
        # if True, show widget body, otherwise show addon configuration page link.
        'complete': True
    }
    ret.update(myscreen.config.to_json())
    return ret
# widget: ここまで
