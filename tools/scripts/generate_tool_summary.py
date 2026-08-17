import json

with open("tools.json", "r") as f:
    tools = json.load(f)


def strip_item(item, root=False):
    if item["model_class"] == "ToolSectionLabel":
        stripped = {
            "model_class": item["model_class"],
            "id": item.get("id"),
            "text": item.get("text"),
            "description": item.get("description"),
        }
    else:
        stripped = {
            "model_class": item["model_class"],
            "id": item.get("id"),
            "name": item.get("name"),
        }

        if not root:
            stripped["description"] = item.get("description")

    elems = item.get("elems")
    if elems is not None:
        stripped["elems"] = [strip_item(elem) for elem in elems]

    return stripped


stripped_tools = [strip_item(tool, root=True) for tool in tools]

with open("tool_summary.json", "w") as summary_file:
    json.dump(stripped_tools, summary_file, indent=2)
    summary_file.write("\n")