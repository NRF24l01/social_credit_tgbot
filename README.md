# Social credit bot

## How to run
### Env config
Create .env with
```
TG_API=Your token
ADMIN_ID=Admin id, easely get from db(tg_id)
```
### Docker build
```bash
docker build soc_credit_tgbot
```
### Run docker
```bash
docker run --env-file .env --name soc_credit_tgbot soc_credit_tgbot 
```

*Profit!)*
