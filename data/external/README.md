# External training datasets

Large third-party training files are downloaded from their official repositories
at runtime rather than copied into this repository.

## ESConv

- Name: Emotional Support Conversation (ESConv)
- Authors: Siyang Liu, Chujie Zheng, Orianna Demasi, Sahand Sabour, Yu Li,
  Zhou Yu, Yong Jiang, and Minlie Huang
- Paper: *Towards Emotional Support Dialog Systems*, ACL 2021
- Official repository: https://github.com/thu-coai/Emotional-Support-Conversation
- Pinned commit: `f262d062ad74cb39b17ea476facc81568ddcba24`
- File: `ESConv.json`
- Conversations: 1,300
- SHA-256: `aa0556c5b330562ba009c1cd5137486bfa2a7255f33225a6524cd58f7efdd9af`
- License restriction: academic research use only

The notebook verifies the checksum before using the file. ESConv is English and
is not postpartum-specific. It teaches emotional-support response behaviour; it
does not replace Umubyeyi's reviewed postpartum knowledge base.

