![Solsets Hero Image](https://uniforge-public.s3.amazonaws.com/solsets_hero.png)

# Solsets Content State Manager

[Solsets](https://solsets.uniforge.io/) are a project by [Uniforge](https://uniforge.io/) to explore digital ownership on the [Solana](https://solana.com/) blockchain. The project consists of three elements,

1. An [on-chain program](https://github.com/uniforge/forge-zero) implementing rights management. Explore the devnet deployment [here](https://explorer.solana.com/address/ForgeZwShFswzeB2FDjRfbGQehFZRpAfQFoH65YG9WZT?cluster=devnet)
2. A [React App](https://github.com/uniforge/forge-zero-react-app) for interacting with the on-chain program
3. A [content state manager](https://github.com/uniforge/content-state-manager) (This repository) which translates the on-chain state into [visual assets](https://solsets.uniforge.io/browse)

## Setup and deployment
Environment setup can be done with the standard `pip` toolset. Deployment is managed via Zappa.
