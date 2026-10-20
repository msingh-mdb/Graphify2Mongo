# Graphify2Mongo
Convert Graphify output into Mongodb collection

This example adapts the node and edge model to a payment platform. It represents systems, API endpoints, queues, databases, payment references, and individual API-call events, then imports a Graphify-style JSON export and traverses it with `$graphLookup`.

Graphify tools do not all export the same schema. The JSON below is an illustrative normalized shape; map your tool's actual field names to `nodes`, `edges`, `source`, and `target` as needed.

## Example Graphify Output
Sample output file is attached [graphifyoutput.json](graphifyoutput.json)

```
{
  "nodes": [
    { "id": "payment:pay-1001", "kind": "Payment", "name": "Payment pay-1001", "properties": { "status": "authorized" } },
    { "id": "call:trace-001:01", "kind": "ApiCall", "name": "Create payment", "traceId": "trace-001", "paymentId": "payment:pay-1001", "properties": { "httpStatus": 202, "latencyMs": 18, "attempt": 1 } },
...],
"edges": [
    { "id": "e01", "source": "payment:pay-1001", "target": "call:trace-001:01", "type": "HAS_CALL", "graph": "payment-trace", "traceId": "trace-001" },
    { "id": "e02", "source": "call:trace-001:01", "target": "api:payments.create", "type": "INVOKES", "graph": "payment-trace", "traceId": "trace-001" },
...]
}
```

## Convert Graphify out to MongoDB collections
Sample python script is attached [load2Mongo.py](load2Mongo.py)
Update the filename for Graphify output file (format matter, code is centered around sample output format)
Add your MongoDB connect string `MONGODB_URI` 
Default DB name will be `payment_graph`, and it will create 2 collections `entities` and `relationships`
Script will create indexes on `relationships` collection (indexes that support our demo use case)

Below is sample from the collection in MonoDB
```
// entities
{
  _id: "system:fraud-service",
  kind: "System",
  name: "Fraud Service",
  properties: { ownerTeam: "Risk Platform", environment: "prod" }
}

// entities: one observed API-call event
{
  _id: "call:trace-001:02",
  kind: "ApiCall",
  name: "Risk evaluation",
  traceId: "trace-001",
  paymentId: "payment:pay-1001",
  properties: { httpStatus: 200, latencyMs: 42, attempt: 1 }
}

// relationships
{
  _id: "edge:e06",
  from: "call:trace-001:02",
  to: "api:risk.evaluate",
  type: "INVOKES",
  graph: "payment-trace",
  traceId: "trace-001",
  active: true
}
```

## $graphLookup aggregation pipeline 
graphLookup up to 10 hops, sorted by hops
```
db.entities.aggregate([
  { $match: { _id: "payment:pay-1001" } },
  {
    $graphLookup: {
      from: "relationships",
      startWith: "$_id",
      connectToField: "from",
      connectFromField: "to",
      as: "Edges",
      maxDepth: 10, 
      depthField: "hop",
      restrictSearchWithMatch: {
        graph: "payment-trace",
        traceId: "trace-001",
        active: true
      }
    }
  },
  {
    $unwind: {
      path: "$Edges"
    }
  },
  {
    $sort: {
      "Edges.hop": 1
    }
  }
]);
```
