// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract DonationPlatform {
    
    // ============================
    // ADMIN ROLE MANAGEMENT
    // ============================

    mapping(address => bool) public admins;

    event AdminAdded(address indexed admin);
    event AdminRemoved(address indexed admin);

    modifier onlyAdmin() {
        require(admins[msg.sender], "Only admin can perform this action");
        _;
    }

    constructor() {
        admins[msg.sender] = true; // deployer = default admin
        emit AdminAdded(msg.sender);
    }

    function addAdmin(address _newAdmin) external onlyAdmin {
        require(!admins[_newAdmin], "Already an admin");
        admins[_newAdmin] = true;
        emit AdminAdded(_newAdmin);
    }

    function removeAdmin(address _admin) external onlyAdmin {
        require(admins[_admin], "Not an admin");
        require(_admin != msg.sender, "Admin cannot remove himself");
        admins[_admin] = false;
        emit AdminRemoved(_admin);
    }

    // ============================
    // CAMPAIGN MANAGEMENT
    // ============================

    enum CampaignStatus { Pending, Approved, Rejected, Disabled }

    struct Campaign {
        address creator;
        string title;
        uint deadline;
        uint totalDonations;
        CampaignStatus status;
    }

    Campaign[] public campaigns;

    event CampaignCreated(
        uint indexed campaignId,
        address indexed creator,
        string title,
        uint deadline
    );

    event DonationReceived(
        uint indexed campaignId,
        address indexed donor,
        uint amount
    );

    event FundsWithdrawn(
        uint indexed campaignId,
        address indexed creator,
        uint amount
    );

    event CampaignApproved(uint indexed campaignId);
    event CampaignRejected(uint indexed campaignId);
    event CampaignDisabled(uint indexed campaignId);

    // Create New Campaign → always Pending first
    function createCampaign(string memory _title, uint _durationMinutes) external {
        require(_durationMinutes > 0, "Duration must be > 0");

        uint deadline = block.timestamp + (_durationMinutes * 1 minutes);

        campaigns.push(
            Campaign({
                creator: msg.sender,
                title: _title,
                deadline: deadline,
                totalDonations: 0,
                status: CampaignStatus.Pending
            })
        );

        emit CampaignCreated(campaigns.length - 1, msg.sender, _title, deadline);
    }

    // ============================
    // CAMPAIGN MODERATION (Admin Only)
    // ============================

    function approveCampaign(uint _id) external onlyAdmin {
        Campaign storage c = campaigns[_id];
        require(c.status == CampaignStatus.Pending, "Not pending");
        c.status = CampaignStatus.Approved;
        emit CampaignApproved(_id);
    }

    function rejectCampaign(uint _id) external onlyAdmin {
        Campaign storage c = campaigns[_id];
        require(c.status == CampaignStatus.Pending, "Not pending");
        c.status = CampaignStatus.Rejected;
        emit CampaignRejected(_id);
    }

    function disableCampaign(uint _id) external onlyAdmin {
        Campaign storage c = campaigns[_id];
        require(c.status == CampaignStatus.Approved, "Only approved can be disabled");
        c.status = CampaignStatus.Disabled;
        emit CampaignDisabled(_id);
    }

    // ============================
    // DONATION LOGIC
    // ============================

    function donateToCampaign(uint _id) external payable {
        Campaign storage c = campaigns[_id];

        require(c.status == CampaignStatus.Approved, "Campaign not approved");
        require(block.timestamp < c.deadline, "Campaign ended");
        require(msg.value > 0, "Donation must be > 0");
        require(msg.sender != c.creator, "Creator cannot donate to own campaign");

        c.totalDonations += msg.value;

        emit DonationReceived(_id, msg.sender, msg.value);
    }

    // ============================
    // WITHDRAW FUNDS
    // ============================

    function withdrawFunds(uint _id) external {
        Campaign storage c = campaigns[_id];

        require(msg.sender == c.creator, "Only creator can withdraw");
        require(block.timestamp >= c.deadline, "Not finished");
        require(c.status == CampaignStatus.Approved, "Only approved campaigns");
        require(c.totalDonations > 0, "No funds available");

        uint amount = c.totalDonations;
        c.totalDonations = 0;

        payable(msg.sender).transfer(amount);

        emit FundsWithdrawn(_id, msg.sender, amount);
    }

    // ============================
    // VIEW FUNCTIONS
    // ============================

    function getCampaignCount() external view returns (uint) {
        return campaigns.length;
    }

    // 🔥 Ditambahkan sesuai permintaan untuk kompatibilitas dengan backend Python
    function getTotalCampaigns() external view returns (uint) {
        return campaigns.length;
    }

    function getCampaign(uint _id) 
        external 
        view 
        returns (
            address creator,
            string memory title,
            uint deadline,
            uint totalDonations,
            CampaignStatus status
        ) 
    {
        Campaign memory c = campaigns[_id];
        return (
            c.creator,
            c.title,
            c.deadline,
            c.totalDonations,
            c.status
        );
    }
}
