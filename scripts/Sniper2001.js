
const Web3 = require('web3')
const net = require('net')
const ethers = require('ethers')
const { concat } = require('ethers/lib/utils')
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

const deposittestWalletKey = (
  "ee9cec01ff03c0adea731d7c5a84f7b412bfd062b9ff35126520b3eb3d5ff258"
)

const deposittestWalletAddress = (
  "0x4DE23f3f0Fb3318287378AdbdE030cf61714b2f3"
)

const sendWalletFlash = new ethers.Wallet(
    "ee9cec01ff03c0adea731d7c5a84f7b412bfd062b9ff35126520b3eb3d5ff258",
    SendproviderFlash,
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

class ScientificNumber {
    constructor(floatWeWant, zeroCount, afterDecimalPointCount) {
    // scientificFloat, scientificPower, zeroCount, afterDecimalPointCount
      this.scientificFloat = floatWeWant
      this.scientificPower = zeroCount + afterDecimalPointCount
      this.zeroCount = zeroCount
      this.afterDecimalPointCount = afterDecimalPointCount;
    }
  }

  const formatIntToScientificFloat = (inttodo) => {
    const intstring = inttodo.toString()
    let tempintstring = intstring
    let zeroCount = 0 //7
    let tempfloatstring = ""
    while (tempintstring.endsWith("0"))
    {
        tempintstring = tempintstring.slice(0, -1);
        zeroCount++
    }
    while (tempintstring.length > 1)
    {
        let lastchar = tempintstring.substr(id.length - 1);
        tempintstring = tempintstring.slice(0, -1);
        tempfloatstring = lastchar + tempfloatstring
    }
    let afterDecimalPointCount = tempfloatstring.length //5

    const stringWeWant = tempintstring + "." + tempfloatstring
    const floatWeWant = parseFloat(stringWeWant)
    return new ScientificNumber(floatWeWant, zeroCount, afterDecimalPointCount)
  }

  const formatScientificFloatToBignumberString = (scifloat) => {
    let bignumberstring = ""    
    let scifloatstring = scifloat.scientificFloat.toString()
    let N = 2 //2nd character
    scifloatstring = scifloatstring.slice(0, N-1) + str.slice(N);
    const B = scifloat.scientificPower-scifloatstring.length-1
    for (let c=0; c < B; c++)
    {
        scifloatstring += "0"
    }
    return bignumberstring
  }

  function numDigitsAfterDecimal(x) {
    var afterDecimalStr = x.toString().split('.')[1] || ''
    return afterDecimalStr.length
  }

  const mulScientificFloats = (scientificNumberOne, scientificNumberTwo) => {
    const fww = scientificNumberOne.scientificFloat*scientificNumberTwo.scientificFloat
    let extraZeros = 0
    let tempfww = fww
    if (fww >= 10)
    {
        tempfww = Math.pow(fww, 1);
        extraZeros++
    }
    const zc = scientificNumberOne.scientificPower+scientificNumberTwo.scientificPower
    const adpc = numDigitsAfterDecimal(tempfww)
    return new ScientificNumber(tempfww, zc+extraZeros, adpc)
  }

  const addScientificFloats = (scientificNumberOne, scientificNumberTwo) => {
    const fww = scientificNumberOne.scientificFloat*scientificNumberTwo.scientificFloat
    let n1 = scientificNumberOne.scientificFloat
    let n2 = scientificNumberTwo.scientificFloat
    for (let i=0;i<scientificNumberOne.scientificPower;i++)
    {
        n1 = n1*10
    }
    for (let i=0;i<scientificNumberTwo.scientificPower;i++)
    {
        n2 = n2*10
    }
    const e1 = BigInt(n1)
    const e2 = BigInt(n2)
    const e3 = e1 + e2
    return formatIntToScientificFloat(e3)
  }
  
  const subScientificFloats = (scientificNumberOne, scientificNumberTwo) => {
    const fww = scientificNumberOne.scientificFloat*scientificNumberTwo.scientificFloat
    let n1 = scientificNumberOne.scientificFloat
    let n2 = scientificNumberTwo.scientificFloat
    for (let i=0;i<scientificNumberOne.scientificPower;i++)
    {
        n1 = n1*10
    }
    for (let i=0;i<scientificNumberTwo.scientificPower;i++)
    {
        n2 = n2*10
    }
    const e1 = BigInt(n1)
    const e2 = BigInt(n2)
    const e3 = e1 - e2
    return formatIntToScientificFloat(e3)
  }
  
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
            //if (value === 0) return
            if (to === addressReceiver) return //eliminates chasing your own tx's or can be set to stop us battling each other to work insynchronously
                if (from === depositWalletAddress) {
                    console.log(`Type: ${type}`)
                if (type === 0) return
                    console.log(`TX MATCHED`)
                    //console.log(`Bandit sending ${value}-ETH \n To-${to} \n GasPrice-${gasPrice} \n GasLimit-${gas}`)
                    //console.log(`Bandit sending ${utils.formatEther(value)}-ETH \n To-${to} \n GasPrice-${utils.formatEther(gasPrice)} \n GasLimit-${gas}`)

                    
                    /*  1ETH = 1,000,000,000,000,000,000 $WEI = 1x10^18 $WEI
                        1ETH = 1,000,000,000 $GWEI = 1x10^9 $GWEI
                        utils.formatEther(wei)   =>   string
                        
                        Format an amount of wei into a decimal string representing the amount
                        of ether. The output will always include at least one whole number 
                        and at least one decimal place, otherwise leading and trailing 0’s 
                        will be trimmed.

                        v = 48366007000

                        ***WE ARE SENDING IN WEI***
                    */

                    const GASPRIORITYCOEFFICIENT = 1.15
                        
                    const noncesend = nonce
                    const bandit = to
                    const valueIn = value
                    const maxPriorityFeePerGasIn = maxPriorityFeePerGas
                    const gasLimIn = gas
                    let gasLimOut = gasLimIn
                    
                    const valueInFORMATTED = formatIntToScientificFloat(valueIn)
                    const maxFeePerGasFORMATTED = formatIntToScientificFloat(maxFeePerGas)
                    const maxPriorityFeePerGasFORMATTED = formatIntToScientificFloat(maxPriorityFeePerGas)
                    const maxPriorityFeePerGasInFORMATTED = formatIntToScientificFloat(maxPriorityFeePerGasIn)
                    console.log(`FORMATTED MAXPRIORITYFEEPERGAS: ${maxPriorityFeePerGasFORMATTED}`)
                    //----------------------ABOVE IS ALL INCOMING VALUES
                    console.log(`break`)

                        //baseFeePerGasBuilder   --NEEDS FIXING OR THROWING INTO ASYNC?
                        //const feeData = await provider.getFeeData()
                        //const maxFeePerGasFromData = feeData.maxFeePerGas
                        //const maxPriorityFeePerGasFromData = feeData.maxPriorityFeePerGas
                        let baseFeePerGas = (maxFeePerGas-maxPriorityFeePerGas)//THIS DOESNT WORK NEEDS GRABBING FROM getFee.Data
                        const baseFeePerGasIn = BigNumber.from(baseFeePerGas)
                        const baseFeePerGasInFORMATTED = subScientificFloats(maxFeePerGasFORMATTED, maxPriorityFeePerGasFORMATTED)
                        //baseFeePerGasBuilder


                        //BALANCE BUILDER
                        const totalGasIn = BigNumber.from(maxPriorityFeePerGasIn*gasLimIn)
                        const totalGasInFORMATTED = mulScientificFloats(maxPriorityFeePerGasInFORMATTED, gasLimInFORMATTED)
                        const balanceBuild = totalGasIn.add(valueIn)
                        const balanceBuildFORMATTED = addScientificFloats(totalGasInFORMATTED, valueInFORMATTED)
                        //BALANCE BUILDER
                        console.log(`breakline`)
                    const gasLimInFORMATTED = formatIntToScientificFloat(gasLimIn)
                    const gasLimOutFORMATTED = formatIntToScientificFloat(gasLimOut)
                    //FIX HERE
                    const maxPriorityFeePerGasOut = BigNumber.from(Math.round(maxPriorityFeePerGasIn*GASPRIORITYCOEFFICIENT))
                    const maxPriorityFeePerGasOutFORMATTED = mulScientificFloats(maxPriorityFeePerGasInFORMATTED, GASPRIORITYCOEFFICIENT)
                    const maxFeePerGasOut = BigNumber.from(baseFeePerGasIn.add(maxPriorityFeePerGasOut))
                    const maxFeePerGasOutFORMATTED = addScientificFloats(baseFeePerGasInFORMATTED, maxPriorityFeePerGasOutFORMATTED)
                    const totalGasOut = BigNumber.from(maxPriorityFeePerGasOut*gasLimOut)
                    const totalGasOutFORMATTED = mulScientificFloats(maxPriorityFeePerGasOutFORMATTED, gasLimOutFORMATTED)
                    const sendv = BigNumber.from(balanceBuild.sub(totalGasOut))
                    const sendvFORMATTED = subScientificFloats(balanceBuildFORMATTED, totalGasOutFORMATTED)
                    
                    // *** VARIABLES ***
                    //
                    // maxFeePerGasOut
                    // maxFeePerGas [DONE]
                    // maxPriorityFeePerGas [DONE]
                    // maxPriorityFeePerGasIn [DONE]
                    // maxPriorityFeePerGasOut [DONE]
                    // maxFeePerGasOut [DONE]
                    // baseFeePerGasIn [DONE]
                    // totalGasOut [DONE]
                    // totalGasIn [DONE]
                    // gasLimOut [DONE]
                    // gasLimIn [DONE]
                    // valueIn [DONE]
                    // balanceBuild [DONE]
                    // sendv [DONE]
                    //
                    // *** IMPORTANT EQUATIONS ***
                    //  maxFeePerGasOut = (maxFeePerGas-maxPriorityFeePerGas)+maxPriorityFeePerGasOut
                    //  totalGasOut = gasLimOut*maxPriorityFeePerGasOut
                    //  totalGasIn = gasLimIn*maxPriorityFeePerGasIn
                    //  maxPriorityFeePerGasOut = Math.round(maxPriorityFeePerGasIn*GASPRIORITYCOEFFICIENT)
                    //  balanceBuild = totalGasIn+valueIn
                    //  sendv = balanceBuild-totalGasOut
                    // ***************************
                    
                    
                    if ( sendv < 0 ) return
                    //FIX HERE
                    console.log(`test---check sendv +maxPriorityFeePerGas+BaseFeePerGas in debugger here - sending out values should be wei`)
                    console.log(`TRYING ${addressReceiver} \n
                                                  SNIPING-${(sendv)}\n 
                                                  totalGas-${(totalGasOut)}\n  
                                                  TotalValue${balanceBuild}\n 
                                                  NONCE-${(noncesend)}\n
                                                  maxPriorityFeePerGasOut-${(maxPriorityFeePerGasOut)}\n
                                                  maxFeePerGasOut-${maxFeePerGasOut}
                                                  GasLimit-${(gasLimOut)}\n 
                                                  SWIPING From ${bandit}`)
                    console.log("DONE")
                    const transaction = {
                      to: addressReceiver,
                      from: depositWalletAddress,
                      nonce: noncesend,
                      value: sendvFORMATTED,
                      chainId: 1,
                      type: 2,
                      maxPriorityFeePerGas: maxPriorityFeePerGasOut, //--USE THIS FOR BRIBING MINERS ✅✅✅✅✅
                      maxFeePerGas: maxFeePerGasOut,
                      gasLimit: gasLimOut,
                      
                    }
                    
                    sendWalletEtherMine.sendTransaction(transaction).then(
                        (_receipt) => {
                            console.log(`SENT TO ${addressReceiver} VIA ETHERMINE✅\n
                                            SNIPED-${(sendv)}✅\n 
                                            balanceBuild-${balanceBuild}✅\n 
                                            totalGas-${(totalGasOut)}✅\n 
                                            NONCE-${(nonce)}✅\n
                                            maxPriorityFeePerGasOut-${(maxPriorityFeePerGasOut)}✅\n
                                            maxFeePerGasOut-${maxFeePerGasOut}
                                            GasLimit-${(gasLimOut)}✅\n 
                                            Stolen From ${bandit}✅`)
                        },
                        (reason) => {
                            console.error('Withdrawal failed', reason)
                        },
                    )
                    
                    
                    
                    
                    sendWallet.sendTransaction(transaction).then(
                        (_receipt) => {
                            console.log(`SENT TO ${addressReceiver} VIA GETH✅\n
                                            SNIPED-${(sendv)}✅\n 
                                            balanceBuild-${balanceBuild}✅\n 
                                            totalGas-${(totalGasOut)}✅\n 
                                            NONCE-${(nonce)}✅\n
                                            maxPriorityFeePerGasOut-${(maxPriorityFeePerGasOut)}✅\n
                                            maxFeePerGasOut-${maxFeePerGasOut}
                                            GasLimit-${(gasLimOut)}✅\n 
                                            Stolen From ${bandit}✅`)
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