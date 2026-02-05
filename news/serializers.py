import xml.etree.ElementTree as ET


def serialize_article(article):
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "approved": article.approved,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "publisher": article.publisher.name if article.publisher else None,
        "journalist": article.journalist.username if article.journalist else None,
    }


def serialize_articles_to_xml(qs):
    root = ET.Element("articles")

    for a in qs:
        node = ET.SubElement(root, "article")
        ET.SubElement(node, "id").text = str(a.id)
        ET.SubElement(node, "title").text = a.title
        ET.SubElement(node, "content").text = a.content
        ET.SubElement(node, "approved").text = "true" if a.approved else "false"
        ET.SubElement(node, "created_at").text = a.created_at.isoformat() if a.created_at else ""
        ET.SubElement(node, "publisher").text = a.publisher.name if a.publisher else ""
        ET.SubElement(node, "journalist").text = a.journalist.username if a.journalist else ""

    return ET.tostring(root, encoding="utf-8")