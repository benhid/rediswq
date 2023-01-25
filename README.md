# Auto Scaling RedisWQ

This repository includes an example for you to use as a reference on how to use [KEDA](https://keda.sh/) to scale a 
work queue based on [Redis Lists](https://redis.io/docs/data-types/lists/).

Workers use Docker-in-Docker (DinD) to run any kind of workload, such as Docker builds, CI/CD pipelines, etc.

For more information on the latter, please check the links below:

* [A Case for Docker-in-Docker on Kubernetes (Part I)](https://applatix.com/case-docker-docker-kubernetes-part/)
* [Running Spacelift CI/CD workers in Kubernetes using DinD](https://spacelift.io/blog/ci-cd-workers-in-kubernetes-dind)

## Prerequisites

You need to have a Redis server running and accessible from your cluster.

Furthermore, you also need to have KEDA installed in Kubernetes.

## Running the pool

The manifest file [worker-pool.yaml](manifests/worker-pool.yaml) can be applied with `kubectl apply`:

> Make sure to replace the `<redis-host>` and `<redis-port>` placeholders with the actual values for your Redis server.

```shell
$ kubectl create namespace rediswq
$ kubectl apply -n rediswq -f manifests/
```

Then add some jobs to the queue and watch the workers pool scale up and down:

```shell
$ export REDIS_HOST=<redis-host>
$ export REDIS_PORT=<redis-port>
$ python producer.py 100
```

## Cleanup

After you are done, you can remove the namespace and all resources:

```shell
$ kubectl delete -n rediswq -f manifests/ 
$ kubectl delete namespace rediswq
```
