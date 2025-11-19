const DonationPlatform = artifacts.require("DonationPlatform");

module.exports = function (deployer) {
  deployer.deploy(DonationPlatform);
};
