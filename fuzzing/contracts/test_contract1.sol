// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FuzzTestContract {

    uint256 public number;
    string public text;
    address public user;
    bool public flag;
    bytes public data;

    event NumberUpdated(uint256 newNumber);
    event TextUpdated(string newText);
    event UserUpdated(address newUser);
    event FlagUpdated(bool newFlag);
    event DataUpdated(bytes newData);

    function setNumber(uint256 _number) public {
        number = _number;
        emit NumberUpdated(_number);
    }

    function setText(string memory _text) public {
        text = _text;
        emit TextUpdated(_text);
    }

    function setUser(address _user) public {
        user = _user;
        emit UserUpdated(_user);
    }

    function setFlag(bool _flag) public {
        flag = _flag;
        emit FlagUpdated(_flag);
    }

    function setData(bytes memory _data) public {
        data = _data;
        emit DataUpdated(_data);
    }

    function complexFunction(uint256 _num, string memory _txt, address _addr, bool _boolVal, bytes memory _byteData) public returns (bool) {
        // just a dummy logic to use all inputs
        number = _num;
        text = _txt;
        user = _addr;
        flag = _boolVal;
        data = _byteData;
        emit NumberUpdated(_num);
        emit TextUpdated(_txt);
        emit UserUpdated(_addr);
        emit FlagUpdated(_boolVal);
        emit DataUpdated(_byteData);
        return true;
    }
}
