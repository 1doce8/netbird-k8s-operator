tests/routes:
	kubectl apply -f tests/crd-route.yaml

tests/groups:
	kubectl apply -f tests/crd-group.yaml

update-crd:
	kubectl delete -f deployments/crd-scheme.yaml
	kubectl apply -f deployments/crd-scheme.yaml

update-ver:
	sudo docker build -t 1doce8/netbird-operator:latest .
	sudo docker push 1doce8/netbird-operator
	kubectl delete -f deployments/deployment.yaml
	kubectl apply -f deployments/deployment.yaml

build:
	sudo docker build -t 1doce8/netbird-operator:latest .
	sudo docker push 1doce8/netbird-operator

redeploy:
	kubectl delete -f deployments/deployment.yaml
	kubectl apply -f deployments/deployment.yaml
