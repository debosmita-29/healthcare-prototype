FROM neo4j:5-community

COPY infra/render/neo4j-entrypoint.sh /neo4j-entrypoint.sh
RUN chmod +x /neo4j-entrypoint.sh

ENTRYPOINT ["tini", "-g", "--", "/neo4j-entrypoint.sh"]
CMD ["neo4j"]
