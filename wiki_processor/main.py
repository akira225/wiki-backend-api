import wikipediaapi
import psycopg2
import pika
import json


def on_request(ch, method, props, body):
    r = json.loads(body)
    if r.get('action') == 'validate':
        response = {'title': article_title(r['data']['article'])}
    elif r.get('action') == 'path':
        response = wiki_find_path(r['data']['A'], r['data']['B'])
    else:
        response = {}
    print(r)
    print(response)
    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id=props.correlation_id),
                     body=json.dumps(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)


db_connection = psycopg2.connect(dbname='wiki', user='zalupa228', password='zalupa228', host='127.0.0.1')
cursor = db_connection.cursor()
wiki_wiki = wikipediaapi.Wikipedia(
    language='ru',
    extract_format=wikipediaapi.ExtractFormat.WIKI
)
banned_articles = set()


def update_banned_articles():
    global banned_articles
    cursor.execute("select article from ban")
    articles = cursor.fetchall()
    for article in articles:
        banned_articles.add(article[0])


def article_title(article):
    a = wiki_wiki.page(article)
    if a.exists():
        return a.displaytitle
    else:
        return None


def wiki_find_path(A, B):
    global banned_articles
    a = wiki_wiki.page(A)
    b = wiki_wiki.page(B)
    if not a.exists() or not b.exists():
        return {'success': False, 'path': None}
    A = a.displaytitle
    B = b.displaytitle
    update_banned_articles()
    if A in banned_articles or B in banned_articles:
        return {'success': False, 'path': None}
    processed_links = dict()
    next_layer = [A]
    processed_links[A] = None
    length = 1
    while True:
        current_layer = list()
        for article in next_layer:
            wiki_page = wiki_wiki.page(article)
            try:
                links = wiki_page.links
            except:
                continue
            for link in links.keys():
                if link == B:
                    processed_links[link] = article
                    return {'success': True, 'path': restore_path(processed_links, B)}
                elif link in processed_links or link in banned_articles:
                    continue
                else:
                    processed_links[link] = article
                    current_layer.append(link)
        length += 1
        next_layer = current_layer


def restore_path(graph, B):
    current = graph.get(B)
    path = [B]
    while current:
        path.insert(0, current)
        current = graph.get(current)
    res = f"{path[0]}"
    del path[0]
    for node in path:
        res += f" -> {node}"
    return res


if __name__ == "__main__":
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='rpc_queue')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='rpc_queue', on_message_callback=on_request)
    channel.start_consuming()
