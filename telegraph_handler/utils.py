from constants import CATEGORIES
from database import database
from constants import DEVICES, POST_CHANNEL_LINK


def menu_generator():
    content = {'tag': 'blockquote', 'children': []}
    for category in CATEGORIES:
        # maybe we have to do more later when issues with the URL appear
        link = category.replace(" ", "-")
        temp = {'tag': 'a', 'attrs': {'href': f'#{link}'}, 'children': [category]}
        content["children"].append(temp)
        content["children"].append(' - ')
    del content['children'][-1]
    real_content = [{'tag': 'hr'}, content, {'tag': 'hr'}]
    return real_content


def main_content_generator():
    temp = []
    for category in CATEGORIES:
        # maybe we have to do more later when issues with the URL appear
        link = category.replace(" ", "-")
        header = {'tag': 'h3', 'children': [{'tag': 'a', 'attrs': {'href': f'#{link}'}, 'children': [category]}]}
        temp.append(header)
        for sub in database.get_subcategories(category):
            sub_header = {'tag': 'h4', 'children': [sub["title"]]}
            temp.append(sub_header)
            devices = {"mobile": [], "desktop": []}
            x = 0
            for device in DEVICES:
                if x <= 3:
                    actual_list = devices["mobile"]
                else:
                    actual_list = devices["desktop"]
                if sub["devices"][device]["message_id"]:
                    message_id = sub["devices"][device]["message_id"]
                    actual_list.append([{'tag': 'a', 'attrs': {'href': f'{POST_CHANNEL_LINK}/{message_id}'},
                                         'children': [transform_device_to_title(device)]}, " | "])
                else:
                    actual_list.append([transform_device_to_title(device), " | "])
                x += 1
            x = 0
            mobile = {'tag': 'p', 'children': ['• ', {'tag': 'strong', 'children': ['Mobile: ']}]}
            desktop = {'tag': 'p', 'children': ['• ', {'tag': 'strong', 'children': ['Desktop: ']}]}
            for section in devices:
                temp_string = ""
                if section == "mobile":
                    to_append = mobile['children']
                else:
                    to_append = desktop['children']
                for result in devices[section]:
                    if isinstance(result[0], str):
                        if not result == devices[section][-1]:
                            temp_string += result[0] + result[1]
                        else:
                            temp_string += result[0]
                            to_append.append(temp_string)
                    elif isinstance(result[0], dict):
                        if not result == devices[section][-1]:
                            if temp_string:
                                to_append.append(temp_string)
                            temp_string = result[1]
                            to_append.append(result[0])
                        else:
                            if temp_string:
                                to_append.append(temp_string)
                            to_append.append(result[0])
            temp.append(mobile)
            temp.append(desktop)
            if sub["help_link"]:
                help_link = {'tag': 'p', 'children': [{'tag': 'a', 'attrs': {'href': sub["help_link"]},
                                                       'children': [{'tag': 'strong', 'children': ['More Help']}]}]}
                temp.append(help_link)
            else:
                pass
            temp.append({'tag': 'p', 'children': [{'tag': 'br'}]})
        footer = menu_generator()
        for content in footer:
            temp.append(content)
    return temp


def transform_device_to_title(device):
    if device == "android":
        return "Android"
    elif device == "android_x":
        return "Android X"
    elif device == "ios":
        return "iOS"
    elif device == "windows_phone":
        return "Windows Phone"
    elif device == "tdesktop":
        return "Linux, Windows, Mac"
    elif device == "macos_native":
        return "MacOS Native"
    elif device == "web":
        return "Web"
