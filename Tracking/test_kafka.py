from kafka import KafkaConsumer, KafkaProducer

bootstrap_servers = ["85.10.200.219:9092"]

consumer = KafkaConsumer('player',bootstrap_servers=bootstrap_servers, api_version=(0,1,0))
consumer.subscribe()

producer = KafkaProducer()

for message in consumer:
    print(message.timestamp)
    # message value and key are raw bytes -- decode if necessary!
    # e.g., for unicode: `message.value.decode('utf-8')`
    print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                          message.offset, message.key,
                                          message.value))