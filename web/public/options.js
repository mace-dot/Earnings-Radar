'use strict';
// Standard long-option expiration arithmetic, independent of forecasts or quotes.
function optionScenario({type,strike,premium,quantity,target}){
 if(!['call','put'].includes(type)||![strike,premium,quantity,target].every(Number.isFinite)||strike<=0||premium<=0||target<0||!Number.isInteger(quantity)||quantity<1||quantity>100)throw new Error('Enter positive strike and premium, whole contracts from 1 to 100, and a nonnegative stock price.');
 const cost=premium*100*quantity,intrinsic=Math.max(type==='call'?target-strike:strike-target,0)*100*quantity;
 if(!Number.isFinite(cost)||!Number.isFinite(intrinsic))throw new Error('Values are too large to calculate reliably.');
 return {cost,maxLoss:cost,breakEven:type==='call'?strike+premium:strike-premium,profitLoss:intrinsic-cost};
}
