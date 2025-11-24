// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DonationPlatform {
    struct Campaign {
        uint256 id;
        address creator;
        string title;
        string description;
        uint256 targetAmount;
        uint256 collectedAmount;
        string imageHash;
        uint256 deadline;
        CampaignStatus status; // 0: Pending, 1: Approved, 2: Rejected, 3: Deleted
        bool fundsWithdrawn;
    }

    enum CampaignStatus { PENDING, APPROVED, REJECTED, DELETED }

    mapping(uint256 => Campaign) public campaigns;
    uint256 public campaignCount = 0;
    address public admin;

    // Events untuk Riwayat Transaksi (Audit Trail)
    event CampaignCreated(uint256 id, string title, address creator, uint256 timestamp);
    event DonationReceived(uint256 campaignId, address donor, uint256 amount, uint256 timestamp);
    event CampaignStatusChanged(uint256 id, CampaignStatus status, uint256 timestamp);
    event CampaignEdited(uint256 id, string newTitle, uint256 timestamp);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function createCampaign(
        string memory _title,
        string memory _description,
        uint256 _targetAmount,
        string memory _imageHash,
        uint256 _durationMinutes
    ) public {
        require(_targetAmount > 0, "Target amount must be greater than 0");
        
        campaigns[campaignCount] = Campaign(
            campaignCount,
            msg.sender,
            _title,
            _description,
            _targetAmount,
            0,
            _imageHash,
            block.timestamp + (_durationMinutes * 1 minutes),
            CampaignStatus.PENDING,
            false
        );

        emit CampaignCreated(campaignCount, _title, msg.sender, block.timestamp);
        campaignCount++;
    }

    function donateToCampaign(uint256 _id) public payable {
        Campaign storage campaign = campaigns[_id];
        require(campaign.status == CampaignStatus.APPROVED, "Campaign is not active");
        require(block.timestamp < campaign.deadline, "Campaign has ended");
        require(msg.value > 0, "Donation must be greater than 0");

        campaign.collectedAmount += msg.value;
        emit DonationReceived(_id, msg.sender, msg.value, block.timestamp);
    }

    // --- FITUR BARU UNTUK ADMIN ---

    function approveCampaign(uint256 _id) public onlyAdmin {
        campaigns[_id].status = CampaignStatus.APPROVED;
        emit CampaignStatusChanged(_id, CampaignStatus.APPROVED, block.timestamp);
    }

    function rejectCampaign(uint256 _id) public onlyAdmin {
        campaigns[_id].status = CampaignStatus.REJECTED;
        emit CampaignStatusChanged(_id, CampaignStatus.REJECTED, block.timestamp);
    }

    // Fitur "Soft Delete" (Hanya Admin)
    function deleteCampaign(uint256 _id) public onlyAdmin {
        campaigns[_id].status = CampaignStatus.DELETED;
        emit CampaignStatusChanged(_id, CampaignStatus.DELETED, block.timestamp);
    }

    // Fitur Edit Campaign (Hanya Admin - karena di blockchain data user immutable, admin yg punya kuasa override)
    function editCampaign(
        uint256 _id,
        string memory _newTitle,
        string memory _newDesc,
        uint256 _newTarget
    ) public onlyAdmin {
        Campaign storage c = campaigns[_id];
        c.title = _newTitle;
        c.description = _newDesc;
        c.targetAmount = _newTarget;
        emit CampaignEdited(_id, _newTitle, block.timestamp);
    }

    function withdrawFunds(uint256 _id) public {
        Campaign storage campaign = campaigns[_id];
        require(msg.sender == campaign.creator || msg.sender == admin, "Unauthorized");
        require(campaign.collectedAmount > 0, "No funds to withdraw");
        require(!campaign.fundsWithdrawn, "Funds already withdrawn");

        campaign.fundsWithdrawn = true;
        payable(campaign.creator).transfer(campaign.collectedAmount);
    }

    function getCampaign(uint256 _id) public view returns (Campaign memory) {
        return campaigns[_id];
    }

    function getCampaignCount() public view returns (uint256) {
        return campaignCount;
    }
}