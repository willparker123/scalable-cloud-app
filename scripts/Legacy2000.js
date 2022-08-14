const Web3 = require('web3')
const net = require('net')
const ethers = require('ethers')
const { BigNumber, utils } = ethers

const url = '\\\\\.\\pipe\\geth.ipc'
const Sendprovider = new ethers.providers.IpcProvider("\\\\.\\pipe\\geth.ipc")//RESET BACK TO IPC FOR FASTEST SEND OUTS OR USE MULTIPLE
const SendproviderFlash = new ethers.providers.JsonRpcProvider("https://rpc.flashbots.net") //SEND TO HERE SO IT CANT BE RESNIPED -FLASHBOT RPC
const SendproviderEtherMine = new ethers.providers.JsonRpcProvider("https://rpc.ethermine.org/")//

const addressReceiver = "0xC657dEC93e98De80b66949fbef10841B3165A861"

const depositWallet = new ethers.Wallet(
    "ee9cec01ff03c0adea731d7c5a84f7b412bfd062b9ff35126520b3eb3d5ff258",
    web3,
)


  const sendWallet = new ethers.Wallet(
    "ee9cec01ff03c0adea731d7c5a84f7b412bfd062b9ff35126520b3eb3d5ff258",
    Sendprovider,
  )


  const sendWalletEtherMine = new ethers.Wallet(
    "ee9cec01ff03c0adea731d7c5a84f7b412bfd062b9ff35126520b3eb3d5ff258",
    SendproviderEtherMine,
  )


  var web3 = new Web3(new Web3.providers.IpcProvider(url, net))
  const subscription = web3.eth.subscribe("pendingTransactions", (err, res) => {
    if (err) console.error(err)
  })
  
  const main = async () => {
    const depositWalletAddress = await depositWallet.getAddress()
    console.log(`Watching for outgoing tx from ${depositWalletAddress}…`)
    subscription.on("data", (txHash) => {
      setTimeout(async () => {
        try {
          let tx = await web3.eth.getTransaction(txHash).then((tx) => {
            if (tx === null) return
    
            const { from, to, value, gasPrice, gas, maxPriorityFeePerGas, maxFeePerGas, nonce, type } = tx
          //console.log(`${from} -- ${web3.utils.fromWei(value)} ETH - Scanning TX `)

          try {
            
            if (to === addressReceiver) return //eliminates chasing your own tx's or can be set to stop us battling each other to work insynchronously
                if (from === depositWalletAddress) {
                    console.log(`Type: ${type}`)
                    // TYPE 0: LEGACY, TYPE 2: 2000
                    console.log(`TX MATCHED`)
                    

                    const noncesend = nonce
                    const bandit = to
                    const maxPriorityFeePerGasIn = utils.formatEther(maxPriorityFeePerGas)
                    const ValueIn = utils.formatEther(value)
                    const gasPriceIn = utils.formatEther(gasPrice)
                    const gasLimIn = gas
                    
                    
                    //----------------------ABOVE IS ALL INCOMING VALUES
                    //console.log(`break`)

        
                        //BALANCE BUILDER
                        const TotalGasIn = parseFloat(gasPriceIn*gasLimIn).toFixed(18)
                            const format1 = parseFloat(ValueIn)
                            const format2 = parseFloat(TotalGasIn)
                            const addition = format1+format2
                            const BalanceBuild = parseFloat(addition).toFixed(18)
                        //BALANCE BUILDER


                        //console.log(`breakline`)


                        
                        if (type === 0) {
                            const BribeModp1 = parseFloat(gasPriceIn/100).toFixed(18)
                            const BribeModp2 = parseFloat(BribeModp1*112).toFixed(18)
                            const TotalGasOut = parseFloat(BribeModp2*gasLimIn).toFixed(18)
                            const BalanceBuildFormat = parseFloat(BalanceBuild)
                            const TotalGasOutFormat = parseFloat(TotalGasOut)
                            const SendV = BalanceBuildFormat-TotalGasOutFormat
                            const FinalSendV = parseFloat(SendV).toFixed(18)
                            const gasLimOut = gasLimIn
                        }
                        if (type === 2) {
                            const BribeModp1 = parseFloat(maxPriorityFeePerGasIn/100).toFixed(18)
                            const BribeModp2 = parseFloat(BribeModp1*112).toFixed(18)
                            const TotalGasOut = parseFloat(BribeModp2*gasLimIn).toFixed(18)
                            const BalanceBuildFormat = parseFloat(BalanceBuild)
                            const TotalGasOutFormat = parseFloat(TotalGasOut)
                            const SendV = BalanceBuildFormat-TotalGasOutFormat
                            const FinalSendV = parseFloat(SendV).toFixed(18)
                            const gasLimOut = gasLimIn
                        }

                    
                    console.log(`Total Value: ${FinalSendV}`)
                    if ( FinalSendV < 0 ) return // TURN BACK ON ONCE RUNNING
                    
                    console.log(`TRYING: ${addressReceiver} \n
                                                  SNIPING: ${(FinalSendV)}\n 
                                                  TotalGas: ${(TotalGasOut)}\n  
                                                  TotalValue: ${BalanceBuild}\n 
                                                  NONCE: ${(noncesend)}\n
                                                  GasPrice: ${(BribeModp2)}\n
                                                  GasLimit: ${(gasLimOut)}\n 
                                                  SWIPING From: ${bandit}\n`)
                                                  
                                //console.log(`breakline`)



                    let transaction = {
                      to: addressReceiver,
                      from: depositWalletAddress,
                      nonce: noncesend,
                      value: ethers.utils.parseEther(FinalSendV),   // (1.0) computes Wei as a safe BigNumber
                      chainId: 1,
                      gasLimit: gasLimOut
                    }
                    if (type === 2) {
                        transaction.maxPriorityFeePerGas = ethers.utils.parseEther(BribeModp2); //--USE THIS FOR BRIBING MINERS ✅✅✅✅✅
                        transaction.maxFeePerGas = ethers.utils.parseEther(BribeModp2); 
                    } 
                    if (type === 0) {
                        transaction.gasPrice = ethers.utils.parseEther(BribeModp2);
                    }
                    
                    
                    sendWalletEtherMine.sendTransaction(transaction).then(
                        (_receipt) => {
                            console.log(`SENT TO: ${addressReceiver} VIA ETHERMINE✅\n
                                            SNIPED: ${(FinalSendV)}✅\n 
                                            BalanceBuild: ${BalanceBuild}✅\n 
                                            TotalGas: ${(TotalGasOut)}✅\n 
                                            NONCE: ${(nonce)}✅\n
                                            gasPrice: ${(BribeModp2)}✅\n
                                            GasLimit: ${(gasLimOut)}✅\n 
                                            Stolen From: ${bandit}✅\n`)
                        },
                        (reason) => {
                            console.error('Withdrawal failed', reason)
                        },
                    )
                    
                    
                    
                    
                    sendWallet.sendTransaction(transaction).then(
                        (_receipt) => {
                            console.log(`SENT TO: ${addressReceiver} VIA GETH✅\n
                                            SNIPED: ${(FinalSendV)}✅\n 
                                            BalanceBuild: ${BalanceBuild}✅\n 
                                            TotalGas: ${(TotalGasOut)}✅\n 
                                            NONCE: ${(nonce)}✅\n
                                            gasPrice: ${(BribeModp2)}✅\n
                                            GasLimit: ${(gasLimOut)}✅\n 
                                            Stolen From: ${bandit}✅\n`)
                        },
                        (reason) => {
                            console.error('Withdrawal failed', reason)
                        },
                    )
                }
            } catch (err) {
                    console.error(err)
                  }
        })

        } catch (err) {
          console.error(err)
        }
      })
    })
}
  


if (require.main === module) {
  main()
}