build:
	sudo docker build -t 1doce8/netbird-operator:latest .
	sudo docker push 1doce8/netbird-operator
redeploy:
	kubectl delete -f k8s.yaml
	kubectl apply -f k8s.yaml
